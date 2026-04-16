# ruff: noqa: D100, D101

from abc import ABC

from graphrecords import Plugin


class Annotator(Plugin, ABC):
    pass
