"""Tests for plugin.py."""

import os
import pytest

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.lib.uploader
import ckanext.resource_indexer.utils as utils


@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "resource_indexer plain_resource_indexer")
class TestPlainIndexer(object):
    def test_resource_is_not_indexed_without_explicit_config_options(
        self, create_with_upload
    ):
        """By default, no files are indexed.

        Every format must be explicitely marked as indexable using CKAN config
        """
        dataset = factories.Dataset()
        create_with_upload(
            "hello world", "file.txt", format="txt", package_id=dataset["id"]
        )

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 0

    @pytest.mark.ckan_config("ckanext.resource_indexer.indexable_formats", "txt json")
    def test_resource_is_indexed_when_format_enabled(self, create_with_upload):
        """Resources with supported formats are indexed.

        Multiple resources can be indexed as a part of the single
        dataset. Unlisted formats still ignored.

        """
        dataset = factories.Dataset()
        create_with_upload(
            "hello world", "file.txt", format="txt", package_id=dataset["id"]
        )
        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 0
        result = helpers.call_action("package_search", q="newer will be here")
        assert result["count"] == 0
        create_with_upload(
            "not here yet", "file.json", format="json", package_id=dataset["id"]
        )
        create_with_upload(
            "newer will be here", "file.html", format="html", package_id=dataset["id"]
        )

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="newer will be here")
        assert result["count"] == 0


@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "resource_indexer pdf_resource_indexer")
class TestPdfIndexer(object):
    @pytest.mark.ckan_config("ckanext.resource_indexer.indexable_formats", "pdf")
    def test_pdf_is_indexed(self, create_with_upload):
        dataset = factories.Dataset()
        path = os.path.join(os.path.dirname(__file__), "data/example.pdf")
        with open(path, "rb") as pdf:
            create_with_upload(
                pdf.read(), "file.pdf", format="pdf", package_id=dataset["id"]
            )

        result = helpers.call_action("package_search", q="Dummy PDF")
        assert result["count"] == 1
