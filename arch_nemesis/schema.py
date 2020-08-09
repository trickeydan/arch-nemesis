"""Configuration for Arch Nemesis."""

from sys import exit
from typing import IO, Any, List

import click
from pydantic import BaseModel, DirectoryPath, Extra, PyObject, ValidationError
from ruamel.yaml import YAML


class Package(BaseModel):
    """A package to build."""

    class Config:
        """Config."""

        extra = Extra.forbid

    name: str
    rel: int = 1
    template: DirectoryPath
    source: PyObject
    source_config: Any


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
