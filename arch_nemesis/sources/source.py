"""A package source."""

from abc import ABCMeta, abstractmethod

from pydantic import BaseModel


class Release:
    """A release."""

    def __init__(
        self,
        source: 'PackageSource',
        version: str,
    ) -> None:
        self.source = source
        self.version = version

    def __eq__(self, other) -> bool:
        return self.version == other.version


class PackageSource(metaclass=ABCMeta):
    """A package source."""

    class ConfigSchema(BaseModel):
        """Config Schema."""

    def __init__(self, config: ConfigSchema) -> None:
        self.config = config

    @abstractmethod
    def get_latest_release(self) -> Release:
        """Get the latest release."""
        raise NotImplementedError

    @abstractmethod
    def get_source_url(self, release: Release) -> str:
        """Get the source url."""
        raise NotImplementedError
