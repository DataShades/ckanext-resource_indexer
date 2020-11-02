# -*- coding: utf-8 -*-

import ckan.plugins.interfaces as interfaces


class IResourceIndexer(interfaces.Interface):
    def get_resource_indexer_weight(res):
        """Defines priority of handler for resource.

        :returns: priority of current plugin
        :rtype: int
        """
        import ckanext.resource_indexer.utils as utils

        return utils.Weight.fallback

    def extract_indexable_chunks(self, path):
        """Convert resource dictionary into chunks of indexable data.

        Chunks can have any form as long as they can be merged into
        package dictionary by implementation of
        IResourceIndexer.merge_chunk_into_index.


        :param path: path to resource file
        :type path: string

        :returns: iterable of all meaningfuld pieces of data
        :rtype: iterable

        """
        return []

    def merge_chunks_into_index(self, pkg_dict, chunks):
        """Merge iterable into index.

        :param pkg_dict: package that is going to be indexed
        :type pkg_dict: dictionary

        :param chunks: collection of data fragments extracted from resource
        :type chunks: iterable
        """
        pass
