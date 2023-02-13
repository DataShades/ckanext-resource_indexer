from __future__ import annotations

import re
import contextlib
import logging
from typing import Any, Optional

import click

from ckan import model
import ckan.plugins.toolkit as tk
from ckan.lib.search import index_for, common

from . import config, utils

log = logging.getLogger(__name__)

RE_WRONG_OFFSET = re.compile(r"offsets must not go backwards startOffset=(?P<start>\d+),endOffset=(?P<end>\d+),lastStartOffset=\d+")

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
                pkg_dict = tk.get_action('package_show')(dict(context), {'id': id_})
                try:
                    package_index.insert_dict(pkg_dict)
                except common.SearchIndexError as e:
                    log.error("Cannot index the package %s because of error: %s", id_, e)
                    if not _suggest_solution(e, pkg_dict):
                        log.exception("Cannot suggest solution for the problem.")

                    continue


def _suggest_solution(err: common.SearchIndexError, pkg_dict: dict[str, Any]) -> bool:
    match = RE_WRONG_OFFSET.search(str(err))
    value = utils.debug_last_content.get()
    if value and match:
        start = int(match.group('start'))
        end = int(match.group('end'))

        # let's add a bit of context
        start = max(0, start - 10)
        end = end + 10

        log.info(
            "The following fragment came from one of the resources"
            " attached to the package with ID %s and cannot be indexed: '%s'."
            " Usually, this error is caused by an unsuitable configuration for the Solr field, which holds indexed content."
            " For example, the field is configured for human-readable text, "
            "while file contents consist of abbreviations, measurement units and numbers.",
            pkg_dict["id"],
            value[start:end]
        )
        return True

    return False
