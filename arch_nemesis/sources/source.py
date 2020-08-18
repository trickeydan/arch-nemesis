"""A package source."""

from abc import ABCMeta, abstractmethod
from typing import Optional

from pydantic import BaseModel


class PackageSource(metaclass=ABCMeta):
    """A package source."""

    class ConfigSchema(BaseModel):
        """Config Schema."""

    def __init__(self, config: ConfigSchema) -> None:
        self.config = config

    @abstractmethod
    def get_latest_release(self) -> Optional[str]:
        """Get the latest release."""
        raise NotImplementedError

    @abstractmethod
    def get_source_url(self) -> str:
        """Get the source url."""
        raise NotImplementedError
