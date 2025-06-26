import re
from typing import TypeVar, get_args
from itertools import zip_longest
from collections.abc import Iterable

T = TypeVar("T")


# By Mike Müller (https://stackoverflow.com/a/38059462)
def zip_varlen(*iterables: list[Iterable[T]], sentinel=object()) -> list[list[T]]:
    return [
        [entry for entry in iterable if entry is not sentinel]
        for iterable in zip_longest(*iterables, fillvalue=sentinel)
    ]  # type: ignore


def split_and_strip(string: str, delimiters: Iterable[str] | str) -> list[str]:
    if isinstance(delimiters, str):
        return [part.strip() for part in string.split(delimiters)]

    string_list = [string]
    for delimiter in delimiters:
        string_list = sum((part.split(delimiter) for part in string_list), [])
    return [part.strip() for part in string_list]


def remove_some_js_comments(string: str):
    string = re.sub(r"\/\*[\W\w]*?\*\/", "", string)  # Remove /* ... */
    return re.sub(r"<!--[\W\w]*?-->", "", string)  # Remove <!-- ... -->


# TODO: this callback_when_false is curse, should be remove
def is_Literal(value, Lit, callback_when_false=lambda _: None):
    if value in get_args(Lit):
        return True
    callback_when_false(value)
    return False


def filter_literal(
    iterable: Iterable, Lit: T, callback_when_false=lambda _: None
) -> list[T]:
    return [value for value in iterable if is_Literal(value, Lit, callback_when_false)]
