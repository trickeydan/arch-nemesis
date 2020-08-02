"""Configuration for Arch Nemesis."""

from sys import exit
from typing import List, IO

import click
from ruamel.yaml import YAML
from pydantic import BaseModel, ConstrainedStr, Extra, constr, DirectoryPath, ValidationError

class Package(BaseModel):
    """A package to build."""

    class Config:
        extra = Extra.forbid

    name: str
    rel: int = 1
    github_repo: constr(regex="^([A-Za-z0-9-_]*)\/([A-Za-z0-9-_]*)$")
    template: DirectoryPath
    allow_prereleases: bool = False
    source_regex: str
    version_regex: str = "(.*)"
    version_group_order: List[int] = []

class Config(BaseModel):
    """Config schema."""

    class Config:
        extra = Extra.forbid

    packages: List[Package]

    @classmethod
    def load_from_yaml(cls, file: IO) -> 'Config':
        """Load from YAML."""
        yaml = YAML(typ='safe')
        data = yaml.load(file)
        try:
            return cls(**data)
        except ValidationError as error:
            click.secho(str(error), fg='red', err=True)
            exit(1)
