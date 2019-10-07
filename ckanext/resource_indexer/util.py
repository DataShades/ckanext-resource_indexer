import logging
import os
import tempfile

import ckan.plugins.toolkit as tk
import requests
import textract
from ckan.lib.uploader import get_resource_uploader

logger = logging.getLogger(__name__)


def select_indexable_resources(resources):
    indexable = []
    for res in resources:
        if res.get('format', '').lower() in tk.aslist(
                tk.config.get('ckanext.resource_indexer.indexable_formats')):
            indexable.append(res)
    return indexable


def index_resource(res, index):
    path = _filepath_for_res_indexing(res)
    if not path:
        return
    fmt = res['format'].lower()
    if fmt == 'pdf':
        try:
            content = textract.process(path, extension='.pdf')
        except Exception as e:
            logger.warn('Problem during extracting content from <%s>: %s',
                        path, e)
            content = ''
    else:
        with open(path) as f:
            content = f.read()
    index.append(content)

    if res['url_type'] != 'upload':
        os.remove(path)


def _filepath_for_res_indexing(res):
    if res['url_type'] == 'upload':
        uploader = get_resource_uploader(res)
        path = uploader.get_path(res['id'])
        if not os.path.exists(path):
            logger.warn('Resource "%s" refers to unexisting path "%s"',
                        res['id'], path)
            return
        return path
    if not tk.asbool(tk.config.get('ckanext.resource_indexer.allow_remote')):
        return
    url = res['url']
    try:
        resp = requests.head(url, timeout=2)
    except Exception as e:
        logger.warn(
            'Unable to make HEAD request for resource %s with url <%s>: %s',
            res['id'], url, e)
        return
    try:
        size = int(resp.headers.get('content-length', 0))
    except ValueError as e:
        logger.warn('Incorrect Content-length header from url <%s>', url)
        return
    if 0 < size < tk.asint(
            tk.config.get('ckanext.resource_indexer.max_remote_size',
                          4)) * 1024 * 1024:
        with tempfile.NamedTemporaryFile(delete=False) as dest:
            resp = requests.get(url)
            dest.write(resp.content)
        return dest.name
