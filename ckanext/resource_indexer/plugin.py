# -*- coding: utf-8 -*-
import logging
import json

import ckan.plugins as p
import ckanext.resource_indexer.interface as interface
import ckanext.resource_indexer.utils as utils

log = logging.getLogger(__name__)


class ResourceIndexerPlugin(p.SingletonPlugin):
    p.implements(p.IPackageController, inherit=True)

    # IPackageController

    def before_index(self, pkg_dict):
        resources = json.loads(pkg_dict["validated_data_dict"]).get("resources", [])
        for res in utils.select_indexable_resources(resources):
            utils.index_resource(res, pkg_dict)
        return pkg_dict


class PdfResourceIndexerPlugin(p.SingletonPlugin):
    p.implements(interface.IResourceIndexer)

    # IResourceIndexer

    def get_resource_indexer_weight(self, res):
        fmt = res["format"].lower()
        if fmt == "pdf":
            return utils.Weight.handler
        return utils.Weight.skip

    def extract_indexable_chunks(self, path):
        return utils.extract_pdf(path)

    def merge_chunks_into_index(self, pkg_dict, chunks):
        return utils.merge_text_chunks(pkg_dict, chunks)


class PlainResourceIndexerPlugin(p.SingletonPlugin):
    p.implements(interface.IResourceIndexer)

    # IResourceIndexer

    def get_resource_indexer_weight(self, res):
        return utils.Weight.fallback

    def extract_indexable_chunks(self, path):
        return utils.extract_plain(path)

    def merge_chunks_into_index(self, pkg_dict, chunks):
        return utils.merge_text_chunks(pkg_dict, chunks)
