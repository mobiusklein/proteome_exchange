import os
import re
import sys
import logging
import multiprocessing

from typing import Dict

import click

from proteome_exchange import get


class ProcessAwareFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = record.__dict__
        try:
            if d['processName'] == "MainProcess":
                d['maybeproc'] = ''
            else:
                d['maybeproc'] = ":%s:" % d['processName'].replace(
                    "Process", '')
        except KeyError:
            d['maybeproc'] = ''
        return super(ProcessAwareFormatter, self).format(record)


class LevelAwareColoredLogFormatter(ProcessAwareFormatter):
    try:
        from colorama import Fore, Style
        # GREY = Fore.WHITE
        GREY = ''
        BLUE = Fore.BLUE
        GREEN = Fore.GREEN
        YELLOW = Fore.YELLOW
        RED = Fore.RED
        BRIGHT = Style.BRIGHT
        DIM = Style.DIM
        BOLD_RED = Fore.RED + Style.BRIGHT
        RESET = Style.RESET_ALL
    except ImportError:
        GREY = ''
        BLUE = ''
        GREEN = ''
        YELLOW = ''
        RED = ''
        BRIGHT = ''
        DIM = ''
        BOLD_RED = ''
        RESET = ''

    def _colorize_field(self, fmt: str, field: str, color: str) -> str:
        return re.sub("(" + field + ")", color + r"\1" + self.RESET, fmt)

    def _patch_fmt(self, fmt: str, level_color: str) -> str:
        fmt = self._colorize_field(fmt, r"%\(asctime\)s", self.GREEN)
        fmt = self._colorize_field(fmt, r"%\(name\).*?s", self.BLUE)
        fmt = self._colorize_field(fmt, r"%\(message\).*?s", self.GREY)
        if level_color:
            fmt = self._colorize_field(fmt, r"%\(levelname\).*?s", level_color)
        return fmt

    def __init__(self, fmt, level_color=None, **kwargs):
        fmt = self._patch_fmt(fmt, level_color=level_color)
        super().__init__(fmt, **kwargs)


class ColoringFormatter(logging.Formatter):
    level_to_color = {
        logging.INFO: LevelAwareColoredLogFormatter.GREEN,
        logging.DEBUG: LevelAwareColoredLogFormatter.GREY + LevelAwareColoredLogFormatter.DIM,
        logging.WARN: LevelAwareColoredLogFormatter.YELLOW + LevelAwareColoredLogFormatter.BRIGHT,
        logging.ERROR: LevelAwareColoredLogFormatter.BOLD_RED,
        logging.CRITICAL: LevelAwareColoredLogFormatter.BOLD_RED,
        logging.FATAL: LevelAwareColoredLogFormatter.RED + LevelAwareColoredLogFormatter.DIM,
    }

    _formatters: Dict[int, LevelAwareColoredLogFormatter]

    def __init__(self, fmt: str, **kwargs):
        self._formatters = {}
        for level, style in self.level_to_color.items():
            self._formatters[level] = LevelAwareColoredLogFormatter(
                fmt, level_color=style, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        fmtr = self._formatters[record.levelno]
        return fmtr.format(record)


def regex_to_filter(pattern):
    pattern = re.compile(pattern)
    return lambda x: pattern.search(str(x)) is not None


@click.group()
def cli():
    logging.basicConfig(
        level="INFO", format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt="%H:%M:%S", handlers=[]
    )
    logger = logging.getLogger()
    format_string = '[%(asctime)s] %(levelname).1s | %(name)s | %(message)s'
    formatter = ProcessAwareFormatter(format_string, datefmt="%H:%M:%S")
    colorized_formatter = ColoringFormatter(format_string, datefmt="%H:%M:%S")
    stderr_handler = logging.StreamHandler(sys.stderr)
    if sys.stderr.isatty():
        stderr_handler.setFormatter(colorized_formatter)
    else:
        stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)


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
@click.option("-f", "--filter", type=str, default=None, help="A regular expression to match file names to download")
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
