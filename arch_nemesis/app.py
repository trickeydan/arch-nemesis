"""Arch Nemesis Command Line Application."""

from pathlib import Path
from shutil import rmtree
from subprocess import check_output
from typing import TextIO, Tuple, cast

import click
from git import Repo
from pydantic import ValidationError

from .schema import Config, Package, SourceInfo
from .sources import PackageSource, Release
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
        for source in package.sources:
            try:
                source.strategy.ConfigSchema(**source.config)
            except ValidationError as error:
                click.secho(f"Error in source config for {package.name}", fg='red', err=True)
                click.secho(str(error), fg='red', err=True)
                exit(1)


@main.command('clean')
@click.option('--cache/--no-cache', default=True, help="Cache downloaded assets")
@click.option(
    '--config',
    default="arch-nemesis.yml",
    type=click.File("r"),
    help="Location of configuration file",
)
def clean(cache: bool, config: TextIO) -> None:
    """Clean up rendered repos."""
    conf = Config.load_from_yaml(config)

    build_dir = Path("build")

    if cache:
        for dire in build_dir.iterdir():
            if dire.stem in map(lambda p: p.name, conf.packages):
                repo = dire / "repo"
                if repo.exists():
                    rmtree(repo)
            else:
                rmtree(dire)
    else:
        rmtree(build_dir)


def process_source(source_info: SourceInfo, build_path: Path, release: Release) -> Tuple[str, str, str]:
    """Process a source to get the URL and checksum."""
    source_config = source_info.strategy.ConfigSchema(**source_info.config)
    source = cast(PackageSource, source_info.strategy(source_config))

    assert release == source.get_latest_release()

    source_url = source.get_source_url(release)

    source_file = download_asset(source_url, build_path)

    file_hash = hash_file(source_file)
    click.secho(f"SHA512: {file_hash}")

    return source_url, file_hash


def process_package(package: Package) -> None:
    """Process a package."""
    click.secho(f"Updating {package.name}", fg='green')

    source_info = package.sources[0]

    source_config = source_info.strategy.ConfigSchema(**source_info.config)
    source = cast(PackageSource, source_info.strategy(source_config))

    release = source.get_latest_release()
    click.secho(f"Latest release: {release.version}")

    build_path = Path("build", package.name)

    source_urls: List[str] = []
    asset_hashes: List[str] = []

    for source_info in package.sources:
        url, checksum = process_source(source_info, build_path, release)
        source_urls.append(url)
        asset_hashes.append(checksum)

    assert len(asset_hashes) == len(source_urls)

    source_str = ""
    for url in source_urls:
        source_str += f"'{url}' "

    checksum_str = ""
    for check in asset_hashes:
        checksum_str += f"'{check}' "

    click.secho(f"Processed {len(asset_hashes)} sources.")

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
        source_str=source_str.strip(),
        checksum_str=checksum_str.strip(),
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
