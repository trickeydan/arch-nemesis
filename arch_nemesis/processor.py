"""Processing."""

from pathlib import Path
from shutil import rmtree
from subprocess import check_output
from typing import Optional, Tuple, cast

import click
from git import Repo

from .schema import Package, SourceInfo
from .sources import PackageSource
from .utils import copy_dir, download_asset, hash_file, parse_pkgbuild


def process_source(
    source_info: SourceInfo,
    build_path: Path,
) -> Tuple[str, str, Optional[str]]:
    """Process a source to get the URL and checksum."""
    source_config = source_info.strategy.ConfigSchema(**source_info.config)
    source = cast(PackageSource, source_info.strategy(source_config))

    source_url = source.get_source_url()

    source_file = download_asset(source_url, build_path)

    file_hash = hash_file(source_file)
    click.secho(f"SHA512: {file_hash}")

    return source_url, file_hash, source.get_latest_release()


def process_package(
    package: Package,
    *,
    commit: bool = True,
    push: bool = True,
) -> None:
    """Process a package."""
    click.secho(f"Updating {package.name}", fg='green')

    build_path = Path("build", package.name)

    source_str = ""
    checksum_str = ""
    release_version = None

    for source_info in package.sources:
        url, checksum, version = process_source(source_info, build_path)
        source_str += f"'{url}' "
        checksum_str += f"'{checksum}' "
        if release_version is None:
            release_version = version
        else:
            if release_version != version:
                raise Exception("Mismatched version between sources.")

    click.secho(f"Processed {len(package.sources)} sources.")
    click.secho(f"Latest release: {release_version}")

    dest = build_path / "repo"

    if dest.exists():
        rmtree(dest)

    click.secho("Cloning from AUR")
    repo = Repo.clone_from(f"ssh://aur@aur.archlinux.org/{package.name}.git", dest)

    pkgbuild = parse_pkgbuild(dest / "PKGBUILD")

    if len(pkgbuild) == 0:
        raise Exception("Seems to be a new package. Not supported yet.")

    rel = int(pkgbuild["pkgrel"])

    click.secho(f"Current pkgrel is {rel}")

    # First iteration
    click.secho("Update repo from template")
    copy_dir(
        package.template,
        dest,
        rel=rel,
        package=package,
        source_str=source_str.strip(),
        checksum_str=checksum_str.strip(),
        version=release_version,
    )

    src_info = check_output(["makepkg", "--printsrcinfo"], cwd=dest)
    src_info_path = dest / ".SRCINFO"
    with src_info_path.open("wb") as fh:
        fh.write(src_info)

    if repo.is_dirty():
        # Update rel
        if pkgbuild["pkgver"] == release_version:
            rel += 1
        else:
            rel = 1
        # Second iteration
        click.secho(f"Updated rel to {rel}")
        # TODO: Reduce code duplication here
        copy_dir(
            package.template,
            dest,
            rel=rel,
            package=package,
            source_str=source_str.strip(),
            checksum_str=checksum_str.strip(),
            version=release_version,
        )

        src_info = check_output(["makepkg", "--printsrcinfo"], cwd=dest)
        src_info_path = dest / ".SRCINFO"
        with src_info_path.open("wb") as fh:
            fh.write(src_info)

        click.secho("Updating AUR")
        if commit:
            repo.git.add(".")
            repo.git.commit("-m", f"Updated to {release_version}")
        if push:
            repo.git.push()
    else:
        click.secho(f"No changes required for {package.name}")
