# -*- coding: utf-8 -*-

import logging
import json

import ckan.plugins as plugins

import ckanext.resource_indexer.interface as interface
import ckanext.resource_indexer.utils as utils

log = logging.getLogger(__name__)


class Resource_IndexerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(interface.IResourceIndexer)

    # IPackageController

    def before_index(self, pkg_dict):
        resources = json.loads(pkg_dict['validated_data_dict']).get(
            'resources', [])
        for res in utils.select_indexable_resources(resources):
            utils.index_resource(res, pkg_dict)
        return pkg_dict

    # IResourceIndexer

    def get_resource_content_extractor(self, res):
        fmt = res['format'].lower()
        return _make_extractor(fmt)

    def get_index_content_combiner(self, res):
        fmt = res['format'].lower()
        return _make_combiner(fmt)


def _make_combiner(fmt):
    def combiner(pkg_dict, res_data):
        text_index = pkg_dict.setdefault('text', [])

        for chunk in res_data:
            if isinstance(chunk, dict):
                pkg_dict.update(chunk)
        else:
            text_index.append(chunk)

    if fmt == 'pdf':
        return utils.Weight.handler, combiner
    else:
        return utils.Weight.fallback, combiner


def _make_extractor(fmt):
    def extractor(path):
        if fmt == 'pdf':
            import textract
            try:
                content = textract.process(path, extension='.pdf')
            except Exception as e:
                log.warn('Problem during extracting content from <%s>',
                         path, exc_info=e)
                content = ''
        else:
            with open(path) as f:
                content = f.read()
        yield content
    if fmt == 'pdf':
        return utils.Weight.handler, extractor
    else:
        return utils.Weight.fallback, extractor
