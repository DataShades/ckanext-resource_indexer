import logging
import os
import tempfile
import enum

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import requests
from ckan.lib.uploader import get_resource_uploader
from ckanext.resource_indexer.interface import IResourceIndexer

log = logging.getLogger(__name__)


class Weight(enum.IntEnum):
    skip = 0
    fallback = 10
    default = 20
    handler = 30
    special = 40
    override = 50


def select_indexable_resources(resources):
    indexable = []
    supported = tk.aslist(tk.config.get("ckanext.resource_indexer.indexable_formats"))
    for res in resources:
        if res.get("format", "").lower() in supported:
            indexable.append(res)
    return indexable


def index_resource(res, pkg_dict):
    path = _filepath_for_res_indexing(res)
    if not path:
        return
    try:
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

        if not handlers:
            return
        handler = handlers[-1]

        chunks = handler.extract_indexable_chunks(path)
        handler.merge_chunks_into_index(pkg_dict, chunks)
    finally:
        if res["url_type"] != "upload":
            os.remove(path)


def _filepath_for_res_indexing(res):
    if res["url_type"] == "upload":
        uploader = get_resource_uploader(res)
        path = uploader.get_path(res["id"])
        if not os.path.exists(path):
            log.warn('Resource "%s" refers to unexisting path "%s"', res["id"], path)
            return
        return path
    if not tk.asbool(tk.config.get("ckanext.resource_indexer.allow_remote")):
        return
    url = res["url"]
    try:
        resp = requests.head(url, timeout=2, allow_redirects=True)
    except Exception as e:
        log.warn(
            "Unable to make HEAD request for resource %s with url <%s>: %s",
            res["id"],
            url,
            e,
        )
        return
    if not resp.ok:
        log.warn(
            "Unsuccessful HEAD request for resource %s with url <%s>. Status code: %s",
            res["id"],
            url,
            resp.status_code,
        )

        return

    try:
        size = int(resp.headers.get("content-length", 0))
    except ValueError:
        log.warn("Incorrect Content-length header from url <%s>", url)
        return
    if (
        0
        < size
        < tk.asint(tk.config.get("ckanext.resource_indexer.max_remote_size", 4))
        * 1024
        * 1024
    ):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as dest:
                resp = requests.get(url)
                dest.write(resp.content)
        except requests.exceptions.RequestException as e:
            log.error(
                "Cannot index remote resource %s with url <%s>: %s", res["id"], url, e
            )
            os.remove(dest.name)
            return
        return dest.name


def merge_text_chunks(pkg_dict, chunks):
    text_index = pkg_dict.setdefault("text", [])
    for chunk in chunks:
        text_index.append(chunk)


def extract_pdf(path):
    import pdftotext

    try:
        with open(path, "rb") as file:
            content = pdftotext.PDF(file)
    except Exception as e:
        log.warn("Problem during extracting content from <%s>", path, exc_info=e)
        content = []
    yield from content


def extract_plain(path):
    with open(path) as f:
        content = f.read()
    yield content
