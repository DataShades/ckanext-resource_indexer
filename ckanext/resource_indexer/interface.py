# -*- coding: utf-8 -*-

import ckan.plugins.interfaces as interfaces


class IResourceIndexer(interfaces.Interface):

    def get_resource_content_extractor(self, res):
        pass
