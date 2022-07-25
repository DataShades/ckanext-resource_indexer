import pytest
from ckanext.resource_indexer import utils

@pytest.fixture
def resources():
    return [
        {"format": fmt}
        for fmt in ["", "pdf", "PDF", "TxT", "CSV"]
    ]


def test_no_indexable_by_default(resources):
    assert list(utils.select_indexable_resources(resources)) == []


@pytest.mark.ckan_config("ckanext.resource_indexer.indexable_formats", "pdf")
def test_case_insensitive_indexable(resources):
    indexable = utils.select_indexable_resources(resources)
    formats = {r["format"] for r in indexable}
    assert formats == {"pdf", "PDF"}
