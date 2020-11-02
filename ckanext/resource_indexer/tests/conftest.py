import six
import pytest
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

from werkzeug.datastructures import FileStorage as FlaskFileStorage


class FakeFileStorage(FlaskFileStorage):
    content_type = None

    def __init__(self, stream, filename):
        self.stream = stream
        self.filename = filename
        self.name = "upload"


@pytest.fixture(scope="session")
def make_resource():
    def factory(content, **kwargs):

        test_file = six.BytesIO()
        test_file.write(
            six.b(content) if isinstance(content, six.text_type) else content
        )
        test_resource = FakeFileStorage(test_file, "Metadata")
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "Metadata",
            "upload": test_resource,
        }
        params.update(kwargs)
        helpers.call_action("resource_create", context, **params)

    return factory
