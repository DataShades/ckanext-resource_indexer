import logging
import os
import tempfile
import enum

import requests

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.lib.uploader import get_resource_uploader

from ckanext.resource_indexer.interface import IResourceIndexer

log = logging.getLogger(__name__)

CONFIG_INDEX_FIELD = "ckanext.resoruce_indexer.index_field"
CONFIG_MAX_REMOTE_SIZE = "ckanext.resource_indexer.max_remote_size"
CONFIG_ALLOW_REMOTE = "ckanext.resource_indexer.allow_remote"
CONFIG_INDEXABLE_FORMATS = "ckanext.resource_indexer.indexable_formats"
CONFIG_BOOST = "ckanext.resoruce_indexer.search_boost"

DEFAULT_INDEX_FIELD = None
DEFAULT_MAX_REMOTE_SIZE = 4
DEFAULT_ALLOW_REMOTE = False
DEFAULT_INDEXABLE_FORMATS = None
DEFAULT_BOOST = 1.0

class Weight(enum.IntEnum):
    skip = 0
    fallback = 10
    default = 20
    handler = 30
    special = 40
    override = 50


def select_indexable_resources(resources):
    """
    Filter out resources with unsupported formats
    Returns a list of resources dicts
    """
    supported = tk.aslist(tk.config.get(CONFIG_INDEXABLE_FORMATS, DEFAULT_INDEXABLE_FORMATS))
    return [res for res in resources if res.get("format", "").lower() in supported]


def index_resource(res, pkg_dict):
    removable_path = _get_removable_filepath_for_resource(res)
    if not removable_path:
        return
    with removable_path as path:
        try:
            handler = _get_handler(res)
            if handler:
                chunks = handler.extract_indexable_chunks(path)
                handler.merge_chunks_into_index(pkg_dict, chunks)
        except Exception as e:
            log.error("An error occured during indexing process: {}".format(e))


def _get_handler(res):
    """
    Handler is a plugin that will provide as with method to index resource
    Based on Weight we are returning the most valuable one
    """
    handlers = [
        plugin
        for (weight, plugin) in sorted(
            [
                (plugin.get_resource_indexer_weight(res), plugin)
                for plugin in p.PluginImplementations(IResourceIndexer)
            ]
        )
        if plugin and weight > 0
    ]

    return handlers[-1] if handlers else None


class StaticPath:
    def __init__(self, path):
        self.path = path

    def __bool__(self):
        return bool(self.path)

    def __enter__(self):
        return self.path

    def __exit__(self, type, value, traceback):
        pass


class RemovablePath(StaticPath):
    def __exit__(self, type, value, traceback):
        os.remove(self.path)


def _get_removable_filepath_for_resource(res):
    """Returns a filepath for a resource that will be indexed"""
    res_id = res["id"]
    res_url = res["url"]

    if res["url_type"] == "upload":
        uploader = get_resource_uploader(res)

        # TODO temporary workaround for ckanext-cloudstorage support
        if p.plugin_loaded("cloudstorage"):
            url = uploader.get_url_from_filename(res_id, res_url)
            filepath = _download_remote_file(res_id, url)
            return RemovablePath(filepath)

        path = uploader.get_path(res_id)
        if not os.path.exists(path):
            log.warn('Resource "%s" refers to unexisting path "%s"', res, path)
            return

        return StaticPath(path)

    if not tk.asbool(tk.config.get(CONFIG_ALLOW_REMOTE, DEFAULT_ALLOW_REMOTE)):
        return

    filepath = _download_remote_file(res_id, res_url)
    return RemovablePath(filepath)


def _download_remote_file(res_id, url):
    """
    Downloads remote resource and save it as temporary file
    Returns path to this file
    """
    try:
        resp = requests.get(url, timeout=2, allow_redirects=True, stream=True)
    except Exception as e:
        log.warn(
            "Unable to make GET request for resource {} with url <{}>: {}".format(
                res_id, url, e
            )
        )
        return

    if not resp.ok:
        log.warn(
            "Unsuccessful GET request for resource {} with url <{}>. \
            Status code: {}".format(
                res_id, url, resp.status_code
            ),
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
    return tk.asint(tk.config.get(CONFIG_MAX_REMOTE_SIZE, DEFAULT_MAX_REMOTE_SIZE)) * 1024 * 1024


def merge_text_chunks(pkg_dict, chunks):
    text_index = pkg_dict.setdefault("text", [])
    if isinstance(text_index, str):
        text_index = [text_index]
        pkg_dict["text"] = text_index

    index_field = tk.config.get(CONFIG_INDEX_FIELD, DEFAULT_INDEX_FIELD)
    str_index = ""

    for chunk in chunks:
        if index_field:
            str_index += str(chunk)
        else:
            text_index.append(chunk)
    if str_index:
        pkg_dict[index_field] = (pkg_dict.get(index_field) or "") + " " + str_index


def extract_pdf(path):
    import pdftotext

    try:
        with open(path, "rb") as file:
            pdf_content = pdftotext.PDF(file)
    except Exception as e:
        log.warn("Problem during extracting content from <{}>".format(path), exc_info=e)
        pdf_content = []
    for page in pdf_content:
        # normalize null-terminated strings that appear in old versions of poppler
        yield page.rstrip("\x00")


def extract_plain(path):
    with open(path) as f:
        content = f.read()
    yield content

def get_boost_string():
    field = tk.config.get(CONFIG_INDEX_FIELD, DEFAULT_INDEX_FIELD)
    try:
        boost = float(tk.config.get(CONFIG_BOOST, DEFAULT_BOOST))
    except (TypeError, ValueError) as e:
        log.error("Cannot parse %s: %s", CONFIG_BOOST, e)
        boost = DEFAULT_BOOST
    if not field or boost == 1:
        return
    if boost.is_integer():
        boost = int(boost)

    return f"{field}^{boost}"
