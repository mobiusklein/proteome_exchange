import os
import re
import multiprocessing

import logging
logging.basicConfig(level='INFO')

import click

from proteome_exchange import get


def regex_to_filter(pattern):
    pattern = re.compile(pattern)
    return lambda x: pattern.search(str(x)) is not None


@click.group()
def cli():
    pass

@cli.command(short_help="List the data files in a data repository through Proteome Exchange")
@click.argument("identifier")
def describe(identifier):
    dataset = get(identifier)
    click.echo("ID: " + dataset.id)
    for df in dataset.dataset_files:
        click.echo("%s - %s" % (df.name, df.file_type))

@cli.command(short_help="Download a data repository through Proteome Exchange")
@click.argument("identifier")
@click.option("-d", "--destination", type=click.Path(dir_okay=True, file_okay=False))
@click.option("-t", "--threads", type=int, default=None)
@click.option("-f", "--filter", type=str, default=None)
def download(identifier, destination=None, threads=None, filter=None):
    if filter is not None:
        filter = regex_to_filter(filter)
    dataset = get(identifier)
    if destination is None:
        destination = identifier
    if not os.path.exists(destination):
        os.makedirs(destination)
    if threads is None:
        threads = multiprocessing.cpu_count()
    dataset.download(destination, filter=filter, threads=threads)


if __name__ == "__main__":
    cli.main()
