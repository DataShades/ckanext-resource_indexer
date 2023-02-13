from __future__ import annotations
from collections.abc import Collection, Container

import logging
from typing import Any, Callable

from werkzeug.utils import import_string

import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)

CONFIG_JSON_AS_TEXT = "ckanext.resoruce_indexer.json.add_as_plain"
DEFAULT_JSON_AS_TEXT = False

CONFIG_INDEX_FIELD = "ckanext.resoruce_indexer.index_field"
DEFAULT_INDEX_FIELD = None

CONFIG_MAX_REMOTE_SIZE = "ckanext.resource_indexer.max_remote_size"
DEFAULT_MAX_REMOTE_SIZE = 4

CONFIG_ALLOW_REMOTE = "ckanext.resource_indexer.allow_remote"
DEFAULT_ALLOW_REMOTE = False

CONFIG_INDEXABLE_FORMATS = "ckanext.resource_indexer.indexable_formats"
DEFAULT_INDEXABLE_FORMATS = None

CONFIG_PLAIN_FORMATS = "ckanext.resource_indexer.plain.indexable_formats"
DEFAULT_PLAIN_FORMATS = ["txt", "csv", "json", "yaml", "yml", "html"]

CONFIG_BOOST = "ckanext.resoruce_indexer.search_boost"
DEFAULT_BOOST = 1.0

CONFIG_JSON_KEY = "ckanext.resoruce_indexer.json.key_processor"
DEFAULT_JSON_KEY = "builtins:str"

CONFIG_JSON_VALUE = "ckanext.resoruce_indexer.json.value_processor"
DEFAULT_JSON_VALUE = "builtins:str"

CONFIG_PFD_PROCESSOR = "ckanext.resoruce_indexer.pdf.page_processor"
DEFAULT_PFD_PROCESSOR = "builtins:str"


def index_json_as_text() -> bool:
    return tk.asbool(tk.config.get(CONFIG_JSON_AS_TEXT, DEFAULT_JSON_AS_TEXT))


def indexable_formats() -> Collection[str]:
    return list({
        f.lower()
        for f in tk.aslist(
                tk.config.get(CONFIG_INDEXABLE_FORMATS, DEFAULT_INDEXABLE_FORMATS)
        )
    })


def plain_formats() -> Container[str]:
    return tk.aslist(
        tk.config.get(CONFIG_PLAIN_FORMATS, DEFAULT_PLAIN_FORMATS)
    )


def allow_remote() -> bool:
    return tk.asbool(tk.config.get(CONFIG_ALLOW_REMOTE, DEFAULT_ALLOW_REMOTE))


def max_remote_size() -> int:
    return tk.asint(
        tk.config.get(CONFIG_MAX_REMOTE_SIZE, DEFAULT_MAX_REMOTE_SIZE)
    )


def index_field() -> str:
    return tk.config.get(CONFIG_INDEX_FIELD, DEFAULT_INDEX_FIELD)


def json_key() -> Callable[[Any], str]:
    return import_string(tk.config.get(CONFIG_JSON_KEY, DEFAULT_JSON_KEY))


def json_value() -> Callable[[Any], str]:
    return import_string(tk.config.get(CONFIG_JSON_VALUE, DEFAULT_JSON_VALUE))


def pdf_processor() -> Callable[[str], str]:
    return import_string(tk.config.get(CONFIG_PFD_PROCESSOR, DEFAULT_PFD_PROCESSOR))


def boost() -> float:
    try:
        return float(tk.config.get(CONFIG_BOOST, DEFAULT_BOOST))
    except (TypeError, ValueError) as e:
        log.error("Cannot parse %s: %s", CONFIG_BOOST, e)
        return DEFAULT_BOOST
