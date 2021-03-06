"""Util functions."""

import hashlib
from pathlib import Path
from re import compile
from shutil import copy
from typing import Any, Dict, List

import click
import requests
from jinja2 import Template


def hash_file(file: Path) -> str:
    """Hash a given file."""
    BLOCK_SIZE = 65536

    file_hash = hashlib.sha512()

    with click.progressbar(length=file.stat().st_size, label="Calculating SHA512") as bar:
        with open(file, "rb") as fh:
            block = fh.read(BLOCK_SIZE)
            while len(block) > 0:
                file_hash.update(block)
                bar.update(BLOCK_SIZE)
                block = fh.read(BLOCK_SIZE)

    return file_hash.hexdigest()


def copy_dir(
    src: Path,
    dest: Path,
    *,
    ignore: List[str] = [".SRCINFO", ".gitignore", ".git"],
    **context: Any,
) -> None:
    """Copy a directory and do templating."""
    if not src.exists() or not src.is_dir():
        raise Exception("Bad template")

    dest.mkdir(exist_ok=True)

    for f in src.rglob("*"):
        rel_f = f.relative_to(src)
        if rel_f.parts[0] not in ignore:
            if rel_f.suffix == ".j2":
                with f.open("r") as fh:
                    data = fh.read()
                template = Template(data)
                output = template.render(**context)

                stripped = f"{rel_f.stem}" + "".join(rel_f.suffixes[:-1])
                new_location = dest / rel_f.parent / stripped

                with new_location.open("w") as fh:
                    fh.write(output)
            else:
                copy(f, dest / rel_f)


def download_asset(url: str, folder: Path) -> Path:
    """Download a file from a url and cache."""
    local_filepath = folder / Path(url.split('/')[-1])

    local_filepath.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()

        try:
            total_size = int(r.headers["Content-Length"])
        except KeyError:
            total_size = 1000

        if local_filepath.exists() and local_filepath.stat().st_size == total_size:
            print("Found in cache")
            return local_filepath

        with click.progressbar(length=total_size, label=f"Fetching {url}") as bar:
            with open(local_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
    return local_filepath


def parse_pkgbuild(path: Path) -> Dict[str, str]:
    """Parse the options in a PKGBUILD."""
    regex = compile("^(.*)[ ]*=[ ]*(.*)[ ]*$")  # TODO: Fix backtracking regex ew

    data: Dict[str, str] = {}

    try:
        with path.open("r") as fh:
            contents = fh.readlines()
            for line in contents:
                match = regex.match(line.strip())
                if match:
                    data[match[1]] = match[2].strip()
    except FileNotFoundError:
        pass
    return data
