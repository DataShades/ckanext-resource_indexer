# ckanext-resource_indexer

Discover more results in the Dataset search by searching through the content of resources.

This extension indexes the content of files attached to resources. In this way
user has more chances to find the relevant results when using site search.

The process if indexation can be customized for each file format via [resource
indexers](#indexers). The following formats are supported out of the box:
* Plain text
* PDF
* JSON

## Structure
* [Installation](#installation)
* [Configuration](#configuration)
* [Indexers](#indexers)
  * [Register own indexer](#register-own-indexer)
  * [Built-in indexers](#built-in-indexers)

## Installation

1. Install the package as a CKAN extension
   ```sh
   pip install ckanext-resource-indexer
   ```
1. Add `resource_indexer` to the list of enabled plugins
1. **Optional**. Enable built-in indexers by adding the following items to the list of enabled plugins:
   * [`plain_resource_indexer`](#plain-indexer)
   * [`pdf_resource_indexer`](#pdf-indexer)
   * [`json_resource_indexer`](#json-indexer)


## Configuration
```ini
# Make an attempt to index remote files(fetch into tmp folder
# using URL)
# (optional, default: false).
ckanext.resource_indexer.allow_remote = 1

# The size treshold(MB) for remote resources
# (optional, default: 4).
ckanext.resource_indexer.max_remote_size = 4

# List of resource formats(lowercase) that should be
# indexed.
# (optional, default: None)
ckanext.resource_indexer.indexable_formats = txt pdf

# Store the data extracted from resource inside specified field in the index.
# If empty, store data inside the general-purpose `text` field.
# (optional, default: text)
ckanext.resoruce_indexer.index_field = extras_res_attachment

# Boost matches by resource's content. Set values greater that 1 in order
# to promote such matches and value between 0 and 1 in order to put such
# matches further in search results. Works only when using custom index
# field(`ckanext.resoruce_indexer.index_field`)
# (optional, default: 1)
ckanext.resoruce_indexer.search_boost = 0.5

##### Indexer specific option ###############

### JSON
# Index JSON files as plain text(in addition to indexing as mapping)
# (optional, default: false)
ckanext.resoruce_indexer.json.add_as_plain = true

# Change a key before it's used for patching the package dictionary
# (optional, default: builtins:str)
ckanext.resoruce_indexer.json.key_processor = custom.module:key_processor

# Change a value before it's used for patching the package dictionary
# (optional, default: builtins:str)
ckanext.resoruce_indexer.json.value_processor = custom.module:value_processor
```

## Indexers

In order to extract the data from resources, this extension uses
**Indexers**. These are CKAN plugins implementing `IResourceIndexer` interface.

For every resource with the format specified by
`ckanext.resource_indexer.indexable_formats` config option, an appropriate
indexer is searched. If no indexers were found(or resource format is missing
from the `ckanext.resource_indexer.indexable_formats` config option), the
resource is skipped.

:information_source: Indexation can be temporarily disabled using one of the
following approaches:
* Set environment variable `CKANEXT_RESOURCE_INDEXER_BYPASS`(any non-empty
value), and the plugin won't interfer into standard dataset indexation
process.
* Use `ckanext.resource_indexer.utils.disabled_indexation` context manager:
  ```python
  with disabled_indexation():
      here_indexation_does_not_happen()

  here_indexation_happens()
  ```


Every indexer has weight(priority). Indexer with the highest weight will be
used to index the resource.

Indexation consists of two steps:

* meaningful data segments extracted from the resource
* these data segments are merged into the package dictionary consumed by the
  search engine(Solr) for indexing

It means, that the format of extracted segments must be compatible with the
merging logic from the second step. But other than that, there are no
particular requirements for the format of extracted data.

Data extraction happens locally. If the resource was uploaded to the local
filesystem, data is extracted directly from the resource's file. If the
resource is stored remotely(either uploaded to the cloud or linked via remote
URL), it can be temporarily downloaded to the local filesystem and removed
after processing. By default, non-local resources are ignored, but this can be
changed via `ckanext.resource_indexer.allow_remote` config option.

### Register own indexer

Implement `ckanext.resource_indexer.interface.IResourceIndexer` by providing following methods:

```python
class CustomIndexerPlugin(plugins.SingletonPlugin):
    plugins.implements(IResourceIndexer)

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
```

### Built-in indexers

#### Plain indexer
Index all the formats specified by `ckanext.resource_indexer.indexable_formats` config option, unless other handler with a non-fallback weight(>10) found.

Resources are indexed as-is. File is read and sent to the index without any additional changes.

Enable it by adding `plain_resource_indexer` to the list of enabled plugins.


#### PDF indexer

Extract and index text from the PDF file.

In order to enable it:
* install current extension with the `pdf` extra:
  ```sh
  pip install 'ckanext-resource-indexer[pdf]'
  ```
* add `pdf_resource_indexer` to the list of enabled plugins and
* install system packages for PDF processing. This will be different depending on your system. Examples:
  * CentOS
     ```sh
     yum install -y pulseaudio-libs-devel \
        gcc-c++ pkgconfig \
        python3-devel \
        libxml2-devel libxslt-devel \
        poppler poppler-utils poppler-cpp-devel
     ```

  * Debian
    ```sh
    apt install build-essential libpoppler-cpp-dev pkg-config python3-dev
    ```

  * macOS
    ```sh
    brew install pkg-config poppler python
    ```

#### JSON indexer

Read a dictionary from the JSON file, convert all non-string values into
strings(i.e, no nested values allowed), and apply it as a patch to the indexed
dataset.

Optionally, if `ckanext.resoruce_indexer.json.add_as_plain` flag enabled, index
the content of the file as a plain-text(similar to the [plain
indexer](#plain-indexer))

If key or value requires preprocessing, specify function that converts data as
a `ckanext.resoruce_indexer.json.key_processor` or
`ckanext.resoruce_indexer.json.value_processor`. It uses standard import-string
format: `module.import.path:function`


Enable it by adding `json_resource_indexer` to the list of enabled plugins.
