"""Class to handle updates."""

from re import compile
from pathlib import Path
from typing import Optional

import click
import requests
from cached_property import cached_property
from github import Github


from .schema import Package

class GitHubManager:
    """Handles github information."""

    def __init__(self, package: Package) -> None:
        self.package = package

        gh = Github("e7c0110cdf64a8fa718c2e4d41dc24c0495ccbbb")
        self.repo = gh.get_repo(package.github_repo)

    @cached_property
    def releases(self):
        """Get the releases."""
        return self.repo.get_releases()

    def get_release_count(self) -> int:
        """Get the number of releases for this repo."""
        return self.releases.totalCount

    def get_most_recent(self):
        """Get the most recent release."""
        if self.package.allow_prereleases:
            return self.releases[0]
        else:
            for release in self.releases:
                if not release.prerelease:
                    return release
        raise Exception("No suitable releases found.")

    def find_source_asset(self, release):
        """Find the right asset."""
        assets = release.get_assets()
        regex = compile(self.package.source_regex)

        candidates = dict()

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
                    assets = sorted(list(candidates.values()), key=lambda x: x.name)
                    return assets[0]
            
            # All the same size
        return list(candidates.values())[0]

    def get_version(self, release) -> str:
        tag = release.tag_name
        regex = compile(self.package.version_regex)
        res = regex.fullmatch(tag)
        if res is None or len(res.groups()) == 0:
            raise Exception("Version does not match regex")
        if len(res.groups()) > 1:
            if len(res.groups()) == len(self.package.version_group_order) == len(set(self.package.version_group_order)):
                version = ""
                for i in self.package.version_group_order:
                    version += res.groups()[i]
                return version
            else:
                raise Exception("Bad Version Group Order")
        return res.groups()[0]

    @classmethod
    def download_asset(cls, asset, folder: Path) -> Path:
        url = asset.browser_download_url
        local_filepath = folder / Path(url.split('/')[-1])
        
        local_filepath.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            
            total_size = int(r.headers["Content-Length"])

            if local_filepath.exists() and local_filepath.stat().st_size == total_size:
                print("Found in cache")
                return local_filepath

            with click.progressbar(length=total_size, label=f"Fetching {asset.name}") as bar:
                with open(local_filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
                        bar.update(len(chunk))
        return local_filepath