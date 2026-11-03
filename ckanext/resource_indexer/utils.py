from __future__ import annotations

import enum
import json
import logging
import os
import tempfile
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import IO, Any

import ckan.plugins as p
import requests
from ckan.lib.uploader import get_resource_uploader

from . import config, exc

try:
    import file_keeper as fk
except ImportError:  # CKAN < 2.12 has no file-keeper storages
    fk = None


log = logging.getLogger(__name__)

bypass_flag = ContextVar("bypass_flag", default=False)
debug_last_content = ContextVar("debug_last_content", default="")


class Weight(enum.IntEnum):
    skip = 0
    fallback = 10
    default = 20
    handler = 30
    special = 40
    override = 50


def select_indexable_resources(
    resources: Iterable[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    """Select resources that supports indexation.

    Returns:
        indexable resources

    """
    supported = config.indexable_formats()
    for res in resources:
        if res.get("format", "").lower() in supported:
            yield res


def index_resource(res: dict[str, Any], pkg_dict: dict[str, Any]):
    """Extract the data from resource and merge it into the package."""
    handler = _get_handler(res)
    if not handler:
        return

    # indexers created before `get_resource_read_limit` was added to the
    # interface do not inherit it
    read_limit = getattr(handler, "get_resource_read_limit", lambda res: 0)(res)

    max_size = config.max_size()

    if max_size and not read_limit and _get_resource_size(res) > max_size:
        log.info(
            "Resource %s of the package %s exceeds the size limit and is not indexed",
            res["id"],
            pkg_dict["id"],
        )
        return

    removable_path = _get_removable_filepath_for_resource(res, read_limit)

    if not removable_path:
        return

    with removable_path as path:
        assert path, "Path cannot be missing"

        try:
            chunks = handler.extract_indexable_chunks(path)
            handler.merge_chunks_into_index(pkg_dict, chunks)
        except Exception:
            log.exception(
                (
                    "File %s(remote files in the temporary filder are not"
                    " persisted) from resource %s of the package %s cannot be"
                    " indexed. Error:"
                ),
                path,
                res["id"],
                pkg_dict["id"],
            )


def _get_resource_size(res: dict[str, Any]) -> int:
    try:
        return int(res.get("size") or 0)
    except (TypeError, ValueError):
        return 0


def text_budget_left(pkg_dict: dict[str, Any]) -> int | None:
    """Number of characters that can still be added to the index field.

    Returns:
        remaining characters or None, if text is not limited
    """
    limit = config.max_text_per_dataset()

    if not limit:
        return None

    current = pkg_dict.get(config.index_field() or "text") or ""

    if isinstance(current, list):
        used = sum(len(str(item)) for item in current)
    else:
        used = len(str(current))

    return max(limit - used, 0)


def _get_handler(res):
    """Handler is a plugin that provides a method to index resource.

    Based on Weight we are returning the most valuable one.
    """
    from ckanext.resource_indexer.interface import IResourceIndexer

    handlers = [
        plugin
        for (weight, plugin) in sorted(
            [
                (plugin.get_resource_indexer_weight(res), plugin)
                for plugin in p.PluginImplementations(IResourceIndexer)
            ],
            key=lambda pair: pair[0],
        )
        if plugin and weight > Weight.skip
    ]

    return handlers[-1] if handlers else None


class StaticPath:
    """With-context for a filepath that should not be modified."""

    def __init__(self, path: str | None):
        self.path = path

    def __bool__(self):
        return bool(self.path)

    def __enter__(self):
        return self.path

    def __exit__(self, type, value, traceback):
        pass


class RemovablePath(StaticPath):
    """With-context for a filepath that must be removed on exit.

    Use it for temporarily downloaded files.
    """

    def __exit__(self, type, value, traceback):
        if self.path:
            os.remove(self.path)


def _get_removable_filepath_for_resource(
    res: dict[str, Any], read_limit: int = 0
) -> StaticPath | None:
    """Returns a context with a path to the file owned by the resource.

    The real path can be extracted from the return value using with-statement:

        >>> result = _get_removable_filepath_for_resource(res)
        >>> if not result:
        >>>     return
        >>> with result as path:
        >>>     do_something_with_path(path)

    If resource contains a link to the remote file(or uploaded via cloudstorage
    plugin), this file can be downloaded, depending on configuration. Files
    uploaded into file-keeper storage(CKAN v2.12+) are always copied into a
    temporary file. After processing, file will be automatically removed.

    When `read_limit` is set, only the first `read_limit` bytes of non-local
    files are downloaded. Otherwise, files bigger than
    `ckanext.resource_indexer.max_size` are ignored.


    """
    res_id = res["id"]
    res_url = res["url"]

    if res.get("url_type") == "upload":
        uploader = get_resource_uploader(res)

        # TODO temporary workaround for ckanext-cloudstorage support
        if p.plugin_loaded("cloudstorage"):
            url = uploader.get_url_from_filename(res_id, res_url)  # type: ignore
            filepath = _download_remote_file(res_id, url, read_limit)
            return RemovablePath(filepath)

        storage = getattr(uploader, "storage", None)
        if fk and isinstance(storage, fk.Storage):
            filepath = _download_storage_file(
                res_id, storage, uploader.get_path(res_id), read_limit
            )
            return RemovablePath(filepath)

        path = uploader.get_path(res_id)
        if not os.path.exists(path):
            log.warning('Resource "%s" refers to unexisting path "%s"', res, path)
            return

        max_size = config.max_size()
        if max_size and not read_limit and os.path.getsize(path) > max_size:
            log.info("Resource %s exceeds the size limit and is not indexed", res_id)
            return

        return StaticPath(path)

    if not config.allow_remote():
        return

    filepath = _download_remote_file(res_id, res_url, read_limit)
    return RemovablePath(filepath)


def _download_remote_file(res_id: str, url: str, read_limit: int = 0) -> str | None:
    """
    Downloads remote resource and save it as temporary file
    Returns path to this file
    """
    try:
        resp = requests.get(
            url,
            timeout=config.remote_timeout(),
            allow_redirects=True,
            stream=True,
        )
    except requests.exceptions.RequestException as e:
        log.warning(
            f"Unable to make GET request for resource {res_id} with url <{url}>: {e}"
        )
        return

    if not resp.ok:
        log.warning(
            f"Unsuccessful GET request for resource {res_id} with url <{url}>.          "
            f"   Status code: {resp.status_code}",
        )

        return

    try:
        size = int(resp.headers.get("content-length", 0))
    except ValueError:
        log.warning(f"Incorrect Content-length header from url <{url}>")
        return

    if 0 < size < _get_remote_res_max_size():
        with resp, tempfile.NamedTemporaryFile(delete=False) as dest:
            try:
                fits = _write_chunks(resp.iter_content(1024 * 64), dest, read_limit)
            except requests.exceptions.RequestException as e:
                log.error(
                    f"Cannot index remote resource {res_id} with url <{url}>: {e}"
                )
                os.remove(dest.name)
                return

        if not fits:
            log.info("Resource %s exceeds the size limit and is not indexed", res_id)
            os.remove(dest.name)
            return

        return dest.name


def _download_storage_file(
    res_id: str, storage: Any, location: str, read_limit: int = 0
) -> str | None:
    """
    Copies resource file from file-keeper storage into temporary file
    Returns path to this file
    """
    with tempfile.NamedTemporaryFile(delete=False) as dest:
        try:
            fits = _write_chunks(
                storage.stream(fk.FileData(fk.Location(location))), dest, read_limit
            )
        # any error of the storage adapter skips the resource
        except Exception as e:  # noqa: BLE001
            log.warning(
                "Cannot read resource %s from storage location <%s>: %s",
                res_id,
                location,
                e,
            )
            os.remove(dest.name)
            return

    if not fits:
        log.info("Resource %s exceeds the size limit and is not indexed", res_id)
        os.remove(dest.name)
        return

    return dest.name


def _write_chunks(chunks: Iterable[bytes], dest: IO[bytes], read_limit: int) -> bool:
    """Copy chunks into the file, stopping after `read_limit` bytes.

    Returns:
        False if the content exceeds `ckanext.resource_indexer.max_size`.
        The limit is not applied when `read_limit` is set.
    """
    max_size = 0 if read_limit else config.max_size()
    written = 0

    for chunk in chunks:
        if read_limit and written + len(chunk) >= read_limit:
            dest.write(chunk[: read_limit - written])
            return True

        written += len(chunk)
        if max_size and written > max_size:
            return False

        dest.write(chunk)

    return True


def _get_remote_res_max_size():
    return config.max_remote_size() * 1024**2


def merge_text_chunks(pkg_dict: dict[str, Any], chunks: Iterable[str]) -> str | None:
    index_field = config.index_field()
    if not index_field:
        index_field = "text"
        pkg_dict.setdefault(index_field, [])

    str_index = "".join(_limit_chunks(chunks, text_budget_left(pkg_dict)))
    if not str_index:
        return

    current = pkg_dict.setdefault(index_field, "")

    if isinstance(current, list):
        pkg_dict[index_field].append(str_index)
        debug_last_content.set(" ".join(pkg_dict[index_field]))

    else:
        pkg_dict[index_field] = " ".join([str(current), str_index])
        debug_last_content.set(pkg_dict[index_field])

    return str_index


def _limit_chunks(chunks: Iterable[str], limit: int | None) -> Iterable[str]:
    """Yield chunks until `limit` characters are produced.

    Remaining chunks are not consumed, so lazy extractors stop early.
    """
    if limit is None:
        yield from chunks
        return

    if limit <= 0:
        return

    for chunk in chunks:
        yield chunk[:limit]
        limit -= len(chunk)

        if limit <= 0:
            return


def extract_pdf(path: str) -> Iterable[str]:
    import pdftotext

    processor = config.pdf_processor()

    with open(path, "rb") as source:
        try:
            pdf_content = pdftotext.PDF(source)
        except UnicodeDecodeError as e:
            raise exc.UnexpectedEncodingError(path, e) from e
        except Exception as e:
            raise exc.UnexpectedContentError(path) from e

    for page in pdf_content:
        # normalize null-terminated strings that appear in old versions of poppler
        content = page.rstrip("\x00")
        processed = processor(content)

        yield processed


def extract_plain(path, limit: int = 0) -> Iterable[str]:
    # we're replacing unknown characters with '�' to avoid UnicodeDecodeError
    # we may want to guess encoding in the future
    with open(path, errors="replace") as f:
        content = f.read(limit or -1)
    yield content


def extract_json(path) -> dict[str, Any]:
    with open(path) as f:
        data = json.load(f)

    key = config.json_key()
    value = config.json_value()

    return {key(k): value(v) for k, v in data.items()}


def get_boost_string():
    field = config.index_field()

    boost = config.boost()

    if not field or boost == 1:
        return
    if boost.is_integer():
        boost = int(boost)

    return f"{field}^{boost}"


def bypass_indexation() -> bool:
    """Check if indexation is disabled.

    May be used for fast index re-builds.
    """
    return bool(os.getenv("CKANEXT_RESOURCE_INDEXER_BYPASS")) or bypass_flag.get()


@contextmanager
def disabled_indexation():
    """With-context that disables indexation of the resource."""
    token = bypass_flag.set(True)
    try:
        yield
    finally:
        bypass_flag.reset(token)
