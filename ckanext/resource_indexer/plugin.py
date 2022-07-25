# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import json
from typing import Any

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.lib.search.query import QUERY_FIELDS

import ckanext.resource_indexer.interface as interface
import ckanext.resource_indexer.utils as utils

log = logging.getLogger(__name__)

CONFIG_JSON_AS_TEXT = "ckanext.resoruce_indexer.json.add_as_plain"
DEFAULT_JSON_AS_TEXT = False


class ResourceIndexerPlugin(p.SingletonPlugin):
    p.implements(p.IPackageController, inherit=True)

    # IPackageController

    def before_dataset_index(self, pkg_dict):
        resources = json.loads(pkg_dict["validated_data_dict"]).get(
            "resources", []
        )

        for res in utils.select_indexable_resources(resources):
            utils.index_resource(res, pkg_dict)
        return pkg_dict

    def before_dataset_search(self, search_params):
        boost = utils.get_boost_string()
        if boost:
            search_params.setdefault("qf", QUERY_FIELDS)
            search_params["qf"] += " " + boost
        return search_params

    before_index = before_dataset_index
    before_search = before_dataset_search


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


class JsonResourceIndexerPlugin(p.SingletonPlugin):
    p.implements(interface.IResourceIndexer)

    def get_resource_indexer_weight(self, res: dict[str, Any]) -> int:
        fmt = res['format'].lower()
        if fmt == 'json':
            return utils.Weight.default
        return utils.Weight.skip

    def extract_indexable_chunks(self, path: str) -> dict[str, Any]:
        return utils.extract_json(path)

    def merge_chunks_into_index(self, pkg_dict: dict[str, Any], chunks: dict[str, Any]):
        pkg_dict.update(chunks)

        if tk.config.get(CONFIG_JSON_AS_TEXT, DEFAULT_JSON_AS_TEXT):
            utils.merge_text_chunks(pkg_dict, [f" {k}: {v}" for k, v in chunks.items()])
