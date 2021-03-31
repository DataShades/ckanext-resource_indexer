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

CONFIG_MAX_REMOTE_SIZE = "ckanext.resource_indexer.max_remote_size"
CONFIG_ALLOW_REMOTE = "ckanext.resource_indexer.allow_remote"
CONFIG_INDEXABLE_FORMATS = "ckanext.resource_indexer.indexable_formats"

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
    supported = tk.aslist(tk.config.get(
        CONFIG_INDEXABLE_FORMATS))
    return [res for res in resources if res.get("format", "").lower() in supported]


def index_resource(res, pkg_dict):
    path = _get_filepath_for_resource(res)
    if not path:
        return

    try:
        handler = _get_handler(res)
        if handler:
            chunks = handler.extract_indexable_chunks(path)
            handler.merge_chunks_into_index(pkg_dict, chunks)
    except Exception as e:
        log.error("An error occured during indexing process: {}".format(e))
    finally:
        if res["url_type"] != "upload" or path.startswith('/tmp/'):
            os.remove(path)


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

    return handlers[-1] if handlers else []


def _get_filepath_for_resource(res):
    """Returns a filepath for a resource that will be indexed"""
    res_id = res['id']
    res_url = res['url']

    if res["url_type"] == "upload":
        uploader = get_resource_uploader(res)

        # TODO temporary workaround for ckanext-cloudstorage support
        if p.plugin_loaded('cloudstorage'):
            url = uploader.get_url_from_filename(res_id, res_url)
            filepath = _download_remote_file(res_id, url)
            return filepath

        path = uploader.get_path(res_id)
        if not os.path.exists(path):
            log.warn('Resource "{res_id}" refers to unexisting path "{path}"')
            return

        return path

    if not tk.asbool(tk.config.get(CONFIG_ALLOW_REMOTE)):
        return

    filepath = _download_remote_file(res_id, res_url)
    return filepath


def _download_remote_file(res_id, url):
    """
    Downloads remote resource and save it as temporary file
    Returns path to this file
    """
    try:
        resp = requests.get(url, timeout=2, allow_redirects=True, stream=True)
    except Exception as e:
        log.warn(
            "Unable to make GET request for resource {} with url <{}>: {}".format(res_id, url, e)
        )
        return

    if not resp.ok:
        log.warn(
            "Unsuccessful GET request for resource {} with url <{}>. \
            Status code: {}".format(res_id, url, resp.status_code),
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
                "Cannot index remote resource {} with url <{}>: {}".format(res_id, url, e)
            )
            os.remove(dest.name)
            return
        return dest.name


def _get_remote_res_max_size():
    return tk.asint(tk.config.get(CONFIG_MAX_REMOTE_SIZE, 4)) * 1024 * 1024


def merge_text_chunks(pkg_dict, chunks):
    text_index = pkg_dict.setdefault("text", [])
    for chunk in chunks:
        text_index.append(chunk)


def extract_pdf(path):
    import pdftotext

    try:
        with open(path, "rb") as file:
            pdf_content = pdftotext.PDF(file)
    except Exception as e:
        log.warn(
            "Problem during extracting content from <{}>".format(path), exc_info=e)
        pdf_content = []
    for page in pdf_content:
        yield page


def extract_plain(path):
    with open(path) as f:
        content = f.read()
    yield content
