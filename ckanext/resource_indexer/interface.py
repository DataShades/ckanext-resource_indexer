# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any

import ckan.plugins.interfaces as interfaces
from ckanext.resource_indexer.utils import Weight

class IResourceIndexer(interfaces.Interface):
    def get_resource_indexer_weight(self, resource: dict[str, Any]) -> int:
        """Define priority of the indexer

        Args:
            resource: resource's details

        Returns:
            the weight of the indexer
            Expected values:
               0: skip handler
               10: use handler if no other handlers found
               20: use handler as a default one for the resource
               30: use handler as an optimal one for the resource
               40: use handler as a special-case handler for the resource
               50: ignore all the other handlers and use this one instead
        """
        return Weight.fallback

    def extract_indexable_chunks(self, path: str) -> Any:
        """Extract indexable data from the resource

        The result can have any form as long as it can be merged into the
        package dictionary by implementation of `merge_chunk_into_index`.

        Args:
            path: path to resource file

        Returns:
            all meaningfuld pieces of data with no type assumption

        """
        return []

    def merge_chunks_into_index(self, pkg_dict: dict[str, Any], chunks: Any):
        """Merge data into the package dictionary.


        Args:
            pkg_dict: package that is going to be indexed
            chunks: collection of data fragments extracted from resource

        Returns:
            all meaningfuld pieces of data with no type assumption
        """
        pass
