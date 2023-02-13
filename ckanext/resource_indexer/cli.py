from __future__ import annotations

import contextlib
import logging

import click

from ckan import model
import ckan.plugins.toolkit as tk
from ckan.lib.search import index_for, common

from . import config

log = logging.getLogger(__name__)


def get_commands():
    return [resource_indexer]


@contextlib.contextmanager
def _patched_config(option, value):
    old = tk.config[option]

    tk.config[option] = value
    try:
        yield
    finally:
        tk.config[option] = old




@click.group(short_help="Include the content of resources into the search-index")
def resource_indexer():
    pass


@resource_indexer.command()
@click.argument("ids", nargs=-1)
@click.option("-f", "--include-format", multiple=True)
@click.option("-F", "--exclude-format", multiple=True)
def rebuild(ids: Collection[str], include_format: tuple[str], exclude_format: tuple[str]):
    formats = {
        *config.indexable_formats(),
        *{f.lower() for f in include_format},
    }

    for f in exclude_format:
        formats.remove(f.lower())

    if not ids:
        ids = [
            r[0] for r in
            model.Session.query(model.Package.id).filter(model.Package.state != 'deleted')
        ]

    package_index = index_for(model.Package)
    context = {'model': model, 'ignore_auth': True, 'validate': False,
        'use_cache': False}

    with _patched_config(config.CONFIG_INDEXABLE_FORMATS, list(formats)):
        with click.progressbar(ids) as bar:
            for id_ in bar:
                try:
                    pkg_dict = tk.get_action('package_show')(dict(context), {'id': id_})
                    package_index.insert_dict(pkg_dict)
                    pass

                except common.SearchIndexError as e:
                    log.exception("Cannot index the package %s because of error: %s", id_, e)
                    log.info("possible solution")
                    continue
