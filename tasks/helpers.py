from os.path import abspath, dirname, join
from typing import Callable

#: Project absolute root path
ROOT = abspath(join(dirname(__file__), ".."))


def color(code: str) -> Callable:
    """A simple ANSI color wrapper factory"""
    return lambda t: "\033[{0}{1}\033[0;m".format(code, t)


green = color("1;32m")
red = color("1;31m")
blue = color("1;30m")
cyan = color("1;36m")
purple = color("1;35m")
white = color("1;39m")


def header(text: str, *args, **kwargs) -> None:
    """Display an header"""
    text = text.format(*args, **kwargs)
    print(" ".join((blue(">>"), cyan(text))))


def info(text: str, *args, **kwargs) -> None:
    """Display informations"""
    text = text.format(*args, **kwargs)
    print(" ".join((purple(">>>"), text)))


def success(text: str, *args, **kwargs) -> None:
    """Display a success message"""
    text = text.format(*args, **kwargs)
    print(" ".join((green("✔"), white(text))))


def error(text: str, *args, **kwargs) -> None:
    """Display an error message"""
    text = text.format(*args, **kwargs)
    print(red("✘ {0}".format(text)))
