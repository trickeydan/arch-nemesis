"""Possible package sources."""

from .github_asset import GitHubAssetSource, GitHubTarSource
from .source import PackageSource, Release

__all__ = ['GitHubAssetSource', 'GitHubTarSource', 'PackageSource', 'Release']
