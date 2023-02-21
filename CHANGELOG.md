# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [0.4.1](https://github.com/DataShades/ckanext-resource_indexer/compare/v0.4.0...v0.4.1) (2023-02-21)


### Bug Fixes

* configurabe timeout for remote requests ([7db13ce](https://github.com/DataShades/ckanext-resource_indexer/commit/7db13ce8b1ccbcf63b1f49338b5a7aa73c736bb4))
* more details about decoding errors from pdf ([2186622](https://github.com/DataShades/ckanext-resource_indexer/commit/2186622f2fecb8f72894e9e4f0110f8207cd7e0a))
* report package/resource ID when indexation fails ([54b6da4](https://github.com/DataShades/ckanext-resource_indexer/commit/54b6da4d4dcf72ce80e4af742795000182e8693b))
* show more details when pdf-parsing failed ([a91bdf8](https://github.com/DataShades/ckanext-resource_indexer/commit/a91bdf862a51c1a27a517094f2639f3a4716bb0e))

## [0.4.0](https://github.com/DataShades/ckanext-resource_indexer/compare/v0.3.2...v0.4.0) (2023-02-13)


### ⚠ BREAKING CHANGES

* restrict plain formats via ckanext.resource_indexer.plain.indexable_formats

### Features

* CLI with rebuild command ([ea0a519](https://github.com/DataShades/ckanext-resource_indexer/commit/ea0a5198875c12b3dd4e47d9ff08e44f26a068de))
* restrict plain formats via ckanext.resource_indexer.plain.indexable_formats ([e6dc626](https://github.com/DataShades/ckanext-resource_indexer/commit/e6dc62630ead46df7ffc91b0ac428c82d895384e))

### [0.3.2](https://github.com/DataShades/ckanext-resource_indexer/compare/v0.3.1...v0.3.2) (2023-02-10)


### Features

* add PDF page processor ([4c4dd55](https://github.com/DataShades/ckanext-resource_indexer/commit/4c4dd555d9a146c128829aab349e1929ecbe7421))

### [0.3.1](https://github.com/DataShades/ckanext-resource_indexer/compare/v0.3.0...v0.3.1) (2022-12-01)


### Features

* disable indexation using `disabled_indexation` context manager ([85d8769](https://github.com/DataShades/ckanext-resource_indexer/commit/85d87697bc65735ae229f5afb01d971f54fcf532))

## [0.3.0](https://github.com/DataShades/ckanext-resource_indexer/compare/v0.2.1...v0.3.0) (2022-12-01)


### ⚠ BREAKING CHANGES

* add config module

### Features

* add config module ([60206cc](https://github.com/DataShades/ckanext-resource_indexer/commit/60206cc1791efef507eae6e6d513934b6f2a57e2))
* bypass indexation using CKANEXT_RESOURCE_INDEXER_BYPASS envvar ([eaeee21](https://github.com/DataShades/ckanext-resource_indexer/commit/eaeee21bee8992c153f4bc0582ca177a8a4c8d66))

## [0.2.0](https://github.com/DataShades/ckanext-resource_indexer/compare/v0.1.2...v0.2.0) (2022-07-25)


### ⚠ BREAKING CHANGES

* Drop Python 2 support

### Features

* Built-in JSON indexer ([af1054a](https://github.com/DataShades/ckanext-resource_indexer/commit/af1054a20c7e224455790e092114aa0213ceab56))
* Drop Python 2 support ([c05ffcf](https://github.com/DataShades/ckanext-resource_indexer/commit/c05ffcfb7f65cb69f7b1421e39960be2096bd935))
