"""Possible package sources."""

from .github_asset import GitHubAssetSource, GitHubTarSource
from .source import PackageSource

__all__ = ['GitHubAssetSource', 'GitHubTarSource', 'PackageSource']
