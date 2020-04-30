# -*- coding: utf-8 -*-

import ckan.plugins.interfaces as interfaces


class IResourceIndexer(interfaces.Interface):

    def get_resource_content_extractor(self, res):
        """
        Provide an ability to implement user content extractor
        That will be used to extract data from package resoruce

        It's a first method that's called. It's decides how exactly
        the data will be extracted. For example, if we have a JSON resource,
        we can extract the data as a key:value pairs, since
        JSON is similair to python dict.

        This method must return the tuple with the weight and extractor
        function itself.
        e.g return 40, extractor

        If the extractor weight is bigger than weight of standard one,
        the custom one will be used.

        :param res: the resource data
        :type res: dictionary

        :returns: the tuple with weight and extractor function
        :rtype: tuple
        """
        pass

    def get_index_content_combiner(self, res):
        """
        Provide an ability to implement user content combiner
        That will be used to add resource extra data to pkg_dict

        This method decides how exactly the resource data will
        be merged with pkg_dict. For example, we can rewrite duplicate keys,
        append or ignore them.

        If the combiner weight is bigger than weight of standard one,
        the custom one will be used.

        :param res: the resource data
        :type res: dictionary

        :returns: the tuple with weight and combiner function
        :rtype: tuple
        """
        pass
