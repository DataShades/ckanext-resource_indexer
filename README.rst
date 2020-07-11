
.. image:: https://travis-ci.org/DataShades/ckanext-resource_indexer.svg?branch=master
    :target: https://travis-ci.org/DataShades/ckanext-resource_indexer

.. image:: https://codecov.io/gh/DataShades/ckanext-resource_indexer/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/DataShades/ckanext-resource_indexer

========================
ckanext-resource_indexer
========================

Index content of resources in addition to metadata.

Important
~~~~~~~~~

master branch of this repository is unstable. Always install **ckanext-resource-indexer** using pip(``pip install ckanext-resource-indexer``) unless you are going to change extension's source code for your need.

---------------
Config Settings
---------------

::

    # The size treshold(MB) for remote resources
    # (optional, default: 4).
    ckanext.resource_indexer.max_remote_size = 4

    # Make an attempt to index remote files(fetch into tmp folder
    # using URL)
    # (optional, default: false).
    ckanext.resource_indexer.allow_remote = 1

    # List of lowercased resource formats that should be
    # indexed. Currently only `pdf` and `txt` supported
    # (optional, default: None)
    ckanext.resource_indexer.indexable_formats = txt pdf

------------------------
Development Installation
------------------------

To install ckanext-resource_indexer for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/DataShades/ckanext-resource_indexer.git
    cd ckanext-resource_indexer
    python setup.py develop

Add ``resource_indexer`` (and optionaly ``pdf_resource_indexer`` or
``plain_resource_indexer``) to the ``ckan.plugins`` setting in your
CKAN config file (by default the config file is located at
``/etc/ckan/default/production.ini``).

-----------------
Running the Tests
-----------------

To run the tests, do::

  pytest --ckan-ini test.ini

---------
AWS Linux
---------

::

   sudo yum install -y pulseaudio-libs-devel python-devel libxml2-devel libxslt-devel poppler poppler-utils
