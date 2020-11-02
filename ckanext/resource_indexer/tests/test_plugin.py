"""Tests for plugin.py."""

import os
import pytest

import ckan.tests.helpers as helpers
import ckan.lib.uploader


@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "resource_indexer plain_resource_indexer")
class TestPlainIndexer(object):
    def test_resource_is_indexed_only_when_format_enabled(
        self, monkeypatch, ckan_config, tmpdir, make_resource
    ):
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, "_storage_path", str(tmpdir))

        make_resource("hello world", format="txt")

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 0

        monkeypatch.setitem(
            ckan_config, "ckanext.resource_indexer.indexable_formats", "txt"
        )

        make_resource("hello world", format="txt")
        make_resource("incorrect format", format="json")

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1
        result = helpers.call_action("package_search", q="incorrect format")
        assert result["count"] == 0

    @pytest.mark.ckan_config("ckanext.resource_indexer.indexable_formats", "txt")
    def test_resource_is_indexed_when_created(
        self, monkeypatch, ckan_config, tmpdir, make_resource
    ):
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, "_storage_path", str(tmpdir))

        make_resource("hello world", format="txt")

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1

        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 0

        make_resource("not here yet", format="txt")

        result = helpers.call_action("package_search", q="hello world")
        assert result["count"] == 1

        result = helpers.call_action("package_search", q="not here yet")
        assert result["count"] == 1


@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "resource_indexer pdf_resource_indexer")
class TestPdfIndexer(object):
    @pytest.mark.ckan_config("ckanext.resource_indexer.indexable_formats", "pdf")
    def test_pdf_is_indexed(self, monkeypatch, ckan_config, tmpdir, make_resource):
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, "_storage_path", str(tmpdir))

        path = os.path.join(os.path.dirname(__file__), "data/example.pdf")
        with open(path, "rb") as pdf:
            make_resource(pdf.read(), format="pdf")

        result = helpers.call_action("package_search", q="Dummy PDF")
        assert result["count"] == 1
