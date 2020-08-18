"""Configuration for Arch Nemesis."""

from sys import exit
from typing import IO, Any, List

import click
from pydantic import BaseModel, DirectoryPath, Extra, PyObject, ValidationError
from ruamel.yaml import YAML


class SourceInfo(BaseModel):
    """Info to get a source."""

    class Config:
        """Config."""

        extra = Extra.forbid

    strategy: PyObject
    config: Any


class Package(BaseModel):
    """A package to build."""

    class Config:
        """Config."""

        extra = Extra.forbid

    name: str
    template: DirectoryPath
    sources: List[SourceInfo]


class Config(BaseModel):
    """Config schema."""

    class Config:
        """Config."""

        extra = Extra.forbid

    packages: List[Package]

    @classmethod
    def load_from_yaml(cls, file: IO[str]) -> 'Config':
        """Load from YAML."""
        yaml = YAML(typ='safe')
        data = yaml.load(file)
        try:
            return cls(**data)  # type: ignore
        except ValidationError as error:
            click.secho(str(error), fg='red', err=True)
            exit(1)
