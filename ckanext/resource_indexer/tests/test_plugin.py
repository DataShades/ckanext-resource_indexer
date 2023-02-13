"""Tests for plugin.py."""

import os
from ckan.lib.search.query import QUERY_FIELDS
import pytest
from unittest import mock

import pysolr
import ckan.tests.helpers as helpers
from ckan.lib.search import rebuild

from ckanext.resource_indexer import config

def dumb_translator(string: str):
    return string.translate(str.maketrans({"P": "X", "D": "Y", "F": "Z"}))


@pytest.mark.usefixtures("with_plugins", "clean_db", "clean_index")
@pytest.mark.ckan_config(
    "ckan.plugins", "resource_indexer plain_resource_indexer"
)
class TestPlainIndexer(object):
    @mock.patch("ckanext.resource_indexer.utils.select_indexable_resources")
    def test_bypassing_indexation(self, selector, monkeypatch, package):
        assert selector.call_count == 0

        rebuild(package["id"])
        assert selector.call_count == 1

        monkeypatch.setenv("CKANEXT_RESOURCE_INDEXER_BYPASS", "1")
        rebuild(package["id"])
        assert selector.call_count == 1

        monkeypatch.setenv("CKANEXT_RESOURCE_INDEXER_BYPASS", "")
        rebuild(package["id"])
        assert selector.call_count == 2

    def test_resource_is_not_indexed_without_explicit_config_options(
        self, create_with_upload, package
    ):
        """By default, no files are indexed.

        Every format must be explicitely marked as indexable using CKAN config
        """
        create_with_upload(
            "hello world", "file.txt", format="txt", package_id=package["id"]
        )

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 0

    @pytest.mark.ckan_config(
        "ckanext.resource_indexer.indexable_formats", "txt json"
    )
    @pytest.mark.ckan_config(
        config.CONFIG_PLAIN_FORMATS, ["json"]
    )

    def test_plain_formats_can_be_changed(
        self, create_with_upload, package
    ):
        create_with_upload(
            "hello world", "file.txt", format="txt", package_id=package["id"]
        )

        create_with_upload(
            "not here yet",
            "file.json",
            format="json",
            package_id=package["id"],
        )
        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 0
        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 1


    @pytest.mark.ckan_config(
        "ckanext.resource_indexer.indexable_formats", "txt json"
    )
    def test_resource_is_indexed_when_format_enabled(
        self, create_with_upload, package
    ):
        """Resources with supported formats are indexed.

        Multiple resources can be indexed as a part of the single
        dataset. Unlisted formats still ignored.

        """
        create_with_upload(
            "hello world", "file.txt", format="txt", package_id=package["id"]
        )
        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 0
        result = helpers.call_action("package_search", q="newer will be here")
        assert result["count"] == 0
        create_with_upload(
            "not here yet",
            "file.json",
            format="json",
            package_id=package["id"],
        )
        create_with_upload(
            "newer will be here",
            "file.html",
            format="html",
            package_id=package["id"],
        )

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="newer will be here")
        assert result["count"] == 0


@pytest.mark.usefixtures("with_plugins", "clean_db", "clean_index")
@pytest.mark.ckan_config(
    "ckan.plugins", "resource_indexer pdf_resource_indexer"
)
class TestPdfIndexer(object):
    @pytest.mark.ckan_config(
        "ckanext.resource_indexer.indexable_formats", "pdf"
    )
    def test_pdf_is_indexed(self, create_with_upload, package):
        path = os.path.join(os.path.dirname(__file__), "data/example.pdf")
        with open(path, "rb") as pdf:
            create_with_upload(
                pdf.read(), "file.pdf", format="pdf", package_id=package["id"]
            )

        result = helpers.call_action("package_search", q="Dummy PDF")
        assert result["count"] == 1

    @pytest.mark.ckan_config(
        "ckanext.resource_indexer.indexable_formats", "pdf"
    )
    @pytest.mark.ckan_config(
        config.CONFIG_PFD_PROCESSOR, "ckanext.resource_indexer.tests.test_plugin:dumb_translator"
    )
    def test_page_processor_applied(self, create_with_upload, package):
        path = os.path.join(os.path.dirname(__file__), "data/example.pdf")
        with open(path, "rb") as pdf:
            create_with_upload(
                pdf.read(), "file.pdf", format="pdf", package_id=package["id"]
            )

        result = helpers.call_action("package_search", q="Yummy XYZ")
        assert result["count"] == 1


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "resource_indexer")
class TestBoost:
    def test_default_index_field_is_not_boosted(self, monkeypatch):
        fn = mock.MagicMock()
        monkeypatch.setattr(pysolr.Solr, "search", fn)
        helpers.call_action("package_search", q="hello")
        assert fn.call_args.kwargs["qf"] == QUERY_FIELDS

    @pytest.mark.ckan_config(config.CONFIG_INDEX_FIELD, "custom_field")
    def test_custom_index_field_without_explicit_boost_ignored(
        self, monkeypatch
    ):
        fn = mock.MagicMock()
        monkeypatch.setattr(pysolr.Solr, "search", fn)
        helpers.call_action("package_search", q="hello")
        assert fn.call_args.kwargs["qf"] == QUERY_FIELDS

    @pytest.mark.ckan_config(config.CONFIG_INDEX_FIELD, "custom_field")
    @pytest.mark.ckan_config(config.CONFIG_BOOST, 2)
    def test_boosted_field(self, monkeypatch):
        fn = mock.MagicMock()
        monkeypatch.setattr(pysolr.Solr, "search", fn)
        helpers.call_action("package_search", q="hello")
        assert fn.call_args.kwargs["qf"] == QUERY_FIELDS + " custom_field^2"

        helpers.call_action("package_search", q="hello", qf="name^1")
        assert fn.call_args.kwargs["qf"] == "name^1 custom_field^2"
