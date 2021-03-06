"""Github Asset Source."""

from abc import abstractmethod
from os import environ
from re import compile
from typing import Any, List, Optional

from github import Github, PaginatedList
from github.GitRelease import GitRelease
from pydantic import BaseModel, Extra, constr

from .source import PackageSource


class GithubBaseClass(PackageSource):
    """Github base class."""

    def __init__(self, config: Any) -> None:
        self.config = config

        if "GITHUB_TOKEN" not in environ:
            raise Exception("Cannot find GITHUB_TOKEN in enviuro")
        gh = Github(environ["GITHUB_TOKEN"])
        self.repo = gh.get_repo(self.config.github_repo)

        self.selected = self._get_most_recent()

    def _get_most_recent(self) -> GitRelease:
        """Get the most recent release."""
        releases: PaginatedList[GitRelease] = self.repo.get_releases()
        if self.config.allow_prereleases:
            return releases[0]
        else:
            for release in releases:
                if not release.prerelease:
                    return release
        raise Exception("No suitable releases found.")

    def _get_version(self, release: GitRelease) -> str:
        tag = release.tag_name
        regex = compile(self.config.version_regex)
        res = regex.fullmatch(tag)
        if res is None or len(res.groups()) == 0:
            raise Exception("Version does not match regex")
        if len(res.groups()) > 1:
            if len(res.groups()) == len(self.config.version_group_order) \
                    == len(set(self.config.version_group_order)):
                version = ""
                for i in self.config.version_group_order:
                    version += res.groups()[i]
                return version
            else:
                raise Exception("Bad Version Group Order")
        return res.groups()[0]

    def _find_source_asset(self, release: GitRelease):
        """Find the right asset."""
        assets = release.get_assets()
        regex = compile(self.config.source_regex)

        candidates = {}

        for asset in assets:
            if regex.fullmatch(asset.name) is not None:
                candidates[asset.name] = asset

        if len(candidates) == 0:
            raise Exception("No valid assets found.")
        elif len(candidates) > 1:
            # Multiple candidates found!

            # Lets check if they are all the same size

            size: Optional[int] = None

            for candidate in candidates.values():
                if size is None:
                    size = candidate.size
                if candidate.size != size:
                    # Multiple distinct assets.
                    assets = sorted(candidates.values(), key=lambda x: x.name)
                    return assets[0]

            # All the same size
        return list(candidates.values())[0]

    def get_latest_release(self) -> Optional[str]:
        """Get the latest release."""
        return self._get_version(self.selected)

    @abstractmethod
    def get_source_url(self) -> str:
        """Get the source url."""
        raise NotImplementedError


class GitHubAssetSource(GithubBaseClass):
    """Github Asset Source."""

    class ConfigSchema(BaseModel):
        """Config Schema."""

        class Config:
            """Config."""

            extra = Extra.forbid

        github_repo: constr(regex=u"^([A-Za-z0-9-_]*)\/([A-Za-z0-9-_]*)$")  # type: ignore
        allow_prereleases: bool = False
        source_regex: str
        version_regex: str = "(.*)"
        version_group_order: List[int] = []

    def get_source_url(self) -> str:
        """Get the source url."""
        return self._find_source_asset(self.selected).browser_download_url


class GitHubTarSource(GithubBaseClass):
    """Github Tar Source."""

    class ConfigSchema(BaseModel):
        """Config Schema."""

        class Config:
            """Config."""

            extra = Extra.forbid

        github_repo: constr(regex=u"^([A-Za-z0-9-_]*)\/([A-Za-z0-9-_]*)$")  # type: ignore
        allow_prereleases: bool = False
        version_regex: str = "(.*)"
        version_group_order: List[int] = []

    def get_source_url(self) -> str:
        """Get the source url."""
        return self.selected.tarball_url
