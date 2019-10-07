# -*- coding: utf-8 -*-

import json

import ckan.plugins as plugins

from ckanext.resource_indexer.util import (select_indexable_resources,
                                           index_resource)


class Resource_IndexerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)

    # IPackageController

    def before_index(self, pkg_dict):
        resources = json.loads(pkg_dict['validated_data_dict']).get(
            'resources', [])
        index = pkg_dict.setdefault('text', [])
        for res in select_indexable_resources(resources):
            index_resource(res, index)
        return pkg_dict
