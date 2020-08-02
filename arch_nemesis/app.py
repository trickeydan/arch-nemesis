"""Arch Nemesis Command Line Application."""

from pathlib import Path
from subprocess import check_output
from shutil import rmtree
from typing import TextIO

import click
from git import Repo

from .schema import Config
from .github import GitHubManager
from .utils import hash_file, copy_dir

@click.group('arch-nemesis')
def main() -> None:
    """Arch Nemesis - AUR Package Updater."""
    pass


@main.command("check")
@click.option('--config', default="arch-nemesis.yml", type=click.File("r"), help="Location of configuration file")
def check(config: TextIO) -> None:
    """Check configuration."""
    Config.load_from_yaml(config)

@main.command("go")
@click.option('--config', default="arch-nemesis.yml", type=click.File("r"), help="Location of configuration file")
def go(config: TextIO) -> None:
    """Update packages."""
    conf = Config.load_from_yaml(config)
    for package in conf.packages:
        click.secho(f"Updating {package.name}", fg='green')
        ghm = GitHubManager(package)
        
        click.secho(f"Found {ghm.get_release_count()} releases.")

        selected = ghm.get_most_recent()
        version = ghm.get_version(selected)
        click.secho(f"Selected release: {selected.title} ({version})")
        source_asset = ghm.find_source_asset(selected)
        click.secho(f"Source file: {source_asset.name}")

        build_path = Path("build", package.name)

        source_file = ghm.download_asset(source_asset, build_path)

        file_hash = hash_file(source_file)
        click.secho(f"SHA512: {file_hash}")

        dest = build_path / "repo"

        if dest.exists():
            rmtree(dest)

        click.secho("Cloning from AUR")
        repo = Repo.clone_from(f"ssh://aur@aur.archlinux.org/{package.name}.git", dest)

        click.secho("Update repo from template")
        copy_dir(
            package.template,
            dest,
            package=package,
            release=selected,
            source_asset=source_asset,
            asset_hash=file_hash,
            version=version,
        )

        src_info = check_output(["makepkg", "--printsrcinfo"], cwd=dest)
        src_info_path = dest / ".SRCINFO"
        with src_info_path.open("wb") as fh:
            fh.write(src_info)

        if repo.is_dirty():
            click.secho("Updating AUR")
            repo.git.add(".")
            repo.git.commit("-m", f"Updated to {selected.title}")
            repo.git.push()
        else:
            click.secho(f"No changes required for {package.name}")
if __name__ == "__main__":
    main()