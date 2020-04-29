#!/bin/bash
set -e

pytest --ckan-ini=subdir/test.ini --cov=ckanext.resource_indexer ckanext/resource_indexer/tests
