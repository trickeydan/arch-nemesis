"""Arch Nemesis Command Line Application."""

from pathlib import Path
from shutil import rmtree
from subprocess import check_output
from typing import TextIO, cast

import click
from git import Repo
from pydantic import ValidationError

from .schema import Config, Package
from .sources import PackageSource
from .utils import copy_dir, download_asset, hash_file


@click.group('arch-nemesis')
def main() -> None:
    """Arch Nemesis - AUR Package Updater."""
    pass


@main.command("check")
@click.option(
    '--config',
    default="arch-nemesis.yml",
    type=click.File("r"),
    help="Location of configuration file",
)
def check(config: TextIO) -> None:
    """Check configuration."""
    conf = Config.load_from_yaml(config)

    # Check source configs
    for package in conf.packages:
        try:
            package.source.ConfigSchema(**package.source_config)
        except ValidationError as error:
            click.secho(f"Error in source config for {package.name}", fg='red', err=True)
            click.secho(str(error), fg='red', err=True)
            exit(1)


def process_package(package: Package) -> None:
    """Process a package."""
    click.secho(f"Updating {package.name}", fg='green')

    source_config = package.source.ConfigSchema(**package.source_config)
    source = cast(PackageSource, package.source(source_config))

    release = source.get_latest_release()
    click.secho(f"Latest release: {release.version}")

    build_path = Path("build", package.name)

    source_url = source.get_source_url(release)

    source_file = download_asset(source_url, build_path)

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
        source_url=source_url,
        asset_hash=file_hash,
        version=release.version,
    )

    src_info = check_output(["makepkg", "--printsrcinfo"], cwd=dest)
    src_info_path = dest / ".SRCINFO"
    with src_info_path.open("wb") as fh:
        fh.write(src_info)

    if repo.is_dirty():
        click.secho("Updating AUR")
        repo.git.add(".")
        repo.git.commit("-m", f"Updated to {release.version}")
        repo.git.push()
    else:
        click.secho(f"No changes required for {package.name}")


@main.command("go")
@click.option(
    '--config',
    default="arch-nemesis.yml",
    type=click.File("r"),
    help="Location of configuration file",
)
@click.option(
    '--package',
    type=click.STRING,
    help="The package to update, defaults to all",
)
@click.option(
    '--ignore-package',
    type=click.STRING,
    help="Update all packages except this one",
)
def go(
    config: TextIO,
    package: str,
    ignore_package: str,
) -> None:
    """Update packages."""
    conf = Config.load_from_yaml(config)

    if package is None:
        for p in conf.packages:
            if ignore_package and ignore_package == p.name:
                click.secho(f"Ignoring {p.name}", fg="magenta")
            else:
                process_package(p)
    else:
        for p in conf.packages:
            if p.name == package:
                process_package(p)


if __name__ == "__main__":
    main()
