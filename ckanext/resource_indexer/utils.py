from __future__ import annotations

import logging
import os
import tempfile
import enum
import json
from typing import Any, Iterable, Optional
from contextvars import ContextVar
from contextlib import contextmanager

import requests

import ckan.plugins as p
from ckan.lib.uploader import get_resource_uploader

from . import config


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
    """Extract the data from resource and merge it into the package.

    """
    removable_path = _get_removable_filepath_for_resource(res)
    if not removable_path:
        return

    with removable_path as path:
        assert path, "Path cannot be missing"

        try:
            handler = _get_handler(res)
            if handler:
                chunks = handler.extract_indexable_chunks(path)
                handler.merge_chunks_into_index(pkg_dict, chunks)
        except Exception as e:
            log.error("An error occured during indexing process: {}".format(e))


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
    """With-context for a filepath that should not be modified.
    """
    def __init__(self, path: Optional[str]):
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


def _get_removable_filepath_for_resource(res: dict[str, Any]) -> Optional[StaticPath]:
    """Returns a context with a path to the file owned by the resource.

    The real path can be extracted from the return value using with-statement:

        >>> result = _get_removable_filepath_for_resource(res)
        >>> if not result:
        >>>     return
        >>> with result as path:
        >>>     do_something_with_path(path)

    If resource contains a link to the remote file(or uploaded via cloudstorage
    plugin), this file can be downloaded, depending on configuration. After
    processing, file will be automatically removed.



    """
    res_id = res["id"]
    res_url = res["url"]

    if res["url_type"] == "upload":
        uploader = get_resource_uploader(res)

        # TODO temporary workaround for ckanext-cloudstorage support
        if p.plugin_loaded("cloudstorage"):
            url = uploader.get_url_from_filename(res_id, res_url)  # type: ignore
            filepath = _download_remote_file(res_id, url)
            return RemovablePath(filepath)

        path = uploader.get_path(res_id)
        if not os.path.exists(path):
            log.warn('Resource "%s" refers to unexisting path "%s"', res, path)
            return

        return StaticPath(path)

    if not config.allow_remote():
        return

    filepath = _download_remote_file(res_id, res_url)
    return RemovablePath(filepath)


def _download_remote_file(res_id: str, url: str) -> Optional[str]:
    """
    Downloads remote resource and save it as temporary file
    Returns path to this file
    """
    try:
        resp = requests.get(url, timeout=2, allow_redirects=True, stream=True)
    except Exception as e:
        log.warn(
            "Unable to make GET request for resource {} with url <{}>: {}"
            .format(res_id, url, e)
        )
        return

    if not resp.ok:
        log.warn(
            "Unsuccessful GET request for resource {} with url <{}>.          "
            "   Status code: {}".format(res_id, url, resp.status_code),
        )

        return

    try:
        size = int(resp.headers.get("content-length", 0))
    except ValueError:
        log.warn("Incorrect Content-length header from url <{}>".format(url))
        return

    if 0 < size < _get_remote_res_max_size():
        dest = tempfile.NamedTemporaryFile(delete=False)
        try:
            with dest:
                for chunk in resp.iter_content(1024 * 64):
                    dest.write(chunk)
        except requests.exceptions.RequestException as e:
            log.error(
                "Cannot index remote resource {} with url <{}>: {}".format(
                    res_id, url, e
                )
            )
            os.remove(dest.name)
            return
        return dest.name


def _get_remote_res_max_size():
    return config.max_remote_size() * 1024**2


def merge_text_chunks(pkg_dict: dict[str, Any], chunks: Iterable[str]) -> Optional[str]:
    index_field = config.index_field()
    if not index_field:
        index_field = "text"
        pkg_dict.setdefault(index_field, [])

    str_index = "".join(chunks)
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


def extract_pdf(path: str) -> Iterable[str]:
    import pdftotext
    processor = config.pdf_processor()

    try:
        with open(path, "rb") as file:
            pdf_content = pdftotext.PDF(file)
    except Exception as e:
        log.warn(
            "Problem during extracting content from <{}>".format(path),
            exc_info=e,
        )
        pdf_content = []
    for page in pdf_content:
        # normalize null-terminated strings that appear in old versions of poppler
        content = page.rstrip("\x00")
        processed = processor(content)

        yield processed


def extract_plain(path) -> Iterable[str]:
    with open(path) as f:
        content = f.read()
    yield content


def extract_json(path) -> dict[str, Any]:
    with open(path) as f:
        try:
            data = json.load(f)
        except ValueError:
            log.exception("Cannot index JSON resource at %s", path)
            return {}

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
    """With-context that disables indexation of the resource.
    """
    token = bypass_flag.set(True)
    try:
        yield
    finally:
        bypass_flag.reset(token)
