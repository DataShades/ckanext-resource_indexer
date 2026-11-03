import pytest

from ckanext.resource_indexer import utils


@pytest.fixture
def resources():
    return [{"format": fmt} for fmt in ["", "pdf", "PDF", "TxT", "CSV"]]


def test_no_indexable_by_default(resources):
    assert list(utils.select_indexable_resources(resources)) == []


@pytest.mark.ckan_config("ckanext.resource_indexer.indexable_formats", "pdf")
def test_case_insensitive_indexable(resources):
    indexable = utils.select_indexable_resources(resources)
    formats = {r["format"] for r in indexable}
    assert formats == {"pdf", "PDF"}


class TestWriteChunks:
    def test_whole_content_without_limits(self, tmp_path):
        dest = tmp_path / "file"
        with dest.open("wb") as f:
            assert utils._write_chunks([b"abc", b"def"], f, 0)

        assert dest.read_bytes() == b"abcdef"

    def test_read_limit(self, tmp_path):
        dest = tmp_path / "file"
        with dest.open("wb") as f:
            assert utils._write_chunks([b"abc", b"def", b"ghi"], f, 4)

        assert dest.read_bytes() == b"abcd"

    @pytest.mark.ckan_config("ckanext.resource_indexer.max_size", "1")
    def test_max_size(self, tmp_path):
        dest = tmp_path / "file"
        chunk = b"x" * 1024**2
        with dest.open("wb") as f:
            assert not utils._write_chunks([chunk, b"x"], f, 0)

    @pytest.mark.ckan_config("ckanext.resource_indexer.max_size", "1")
    def test_read_limit_ignores_max_size(self, tmp_path):
        dest = tmp_path / "file"
        chunk = b"x" * 1024**2
        read_limit = 1024**2 + 10
        with dest.open("wb") as f:
            assert utils._write_chunks([chunk, chunk], f, read_limit)

        assert dest.read_bytes() == b"x" * read_limit


class TestTextLimit:
    def test_no_budget_by_default(self):
        assert utils.text_budget_left({"text": ["abc"]}) is None

    @pytest.mark.ckan_config("ckanext.resource_indexer.max_text_per_dataset", "5")
    def test_budget(self):
        assert utils.text_budget_left({}) == 5
        assert utils.text_budget_left({"text": ["ab", "c"]}) == 2
        assert utils.text_budget_left({"text": "abcdefg"}) == 0

    @pytest.mark.ckan_config("ckanext.resource_indexer.max_text_per_dataset", "5")
    def test_merge_is_truncated(self):
        pkg_dict = {"text": ["ab"]}
        utils.merge_text_chunks(pkg_dict, ["cd", "ef", "gh"])
        assert pkg_dict["text"] == ["ab", "cde"]

    def test_limit_chunks_stops_consuming(self):
        consumed = []

        def chunks():
            for chunk in ["abc", "def", "ghi"]:
                consumed.append(chunk)
                yield chunk

        assert list(utils._limit_chunks(chunks(), 4)) == ["abc", "d"]
        assert consumed == ["abc", "def"]


def test_extract_plain_limit(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("hello world")

    assert list(utils.extract_plain(str(path), 5)) == ["hello"]
    assert list(utils.extract_plain(str(path))) == ["hello world"]
