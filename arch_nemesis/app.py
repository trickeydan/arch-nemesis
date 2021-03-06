"""Arch Nemesis Command Line Application."""

from pathlib import Path
from shutil import rmtree
from typing import TextIO

import click
from pydantic import ValidationError

from arch_nemesis import __version__

from .processor import process_package
from .schema import Config


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
                click.secho(
                    f"Error in source config for {package.name}",
                    fg='red',
                    err=True,
                )
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
@click.option(
    '--push/--no-push',
    default=True,
    help="Specify if commits should be pushed to the AUR, defaults to True",
)
@click.option(
    '--commit/--no-commit',
    default=True,
    help="Specify if changes should be committed automatically, defaults to True",
)
def go(
    config: TextIO,
    package: str,
    ignore_package: str,
    push: bool,
    commit: bool,
) -> None:
    """Update packages."""
    conf = Config.load_from_yaml(config)

    if push and not commit:
        click.secho(
            "Warning: Pushing and not committing may have unexpected results.",
            err=True,
            fg="yellow",
        )

    if package is None:
        for p in conf.packages:
            if ignore_package and ignore_package == p.name:
                click.secho(f"Ignoring {p.name}", fg="magenta")
            else:
                process_package(p, push=push, commit=commit)
    else:
        for p in conf.packages:
            if p.name == package:
                process_package(p, push=push, commit=commit)


@main.command("version")
def version() -> None:
    """Print the current version."""
    click.echo(__version__)


if __name__ == "__main__":
    main()
