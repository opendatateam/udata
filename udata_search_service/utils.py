from math import log

from bs4 import BeautifulSoup
from markdown import markdown


def get_concat_title_org(title: str, acronym: str, organization_name: str) -> str:
    concat = title
    if acronym:
        concat += " " + acronym
    if organization_name:
        concat += " " + organization_name
    return concat


def log2p(value):
    """
    Add 2 to the field value and take the common logarithm.
    It makes sure that the result is > 0, needed for function score
    Using multiply boost mode
    """
    if not value:
        value = 0
    return log(value + 2)


def mdstrip(value):
    """
    Truncate and strip tags from a markdown source

    The markdown source is truncated at the excerpt if present and
    smaller than the required length. Then, all html tags are stripped.
    """
    if not value:
        return ""
    rendered = markdown(value, wrap=False)
    text = "".join(BeautifulSoup(rendered, "html.parser").findAll(text=True))
    return text
