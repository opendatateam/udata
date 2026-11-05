"""
Shared building blocks for the ``.../suggest/`` autocomplete endpoints.

Historically every suggest endpoint (datasets, organizations, reuses, users,
tags, spatial zones, ...) reimplemented its own matching and sorting, with
inconsistent behaviour:

- accent-sensitivity: a plain ``name__icontains`` matches "Orléans" but not
  "orleans", so typing without accents returned nothing;
- no match-quality ranking: an exact match, a prefix match and a match buried
  in the middle of a word ("paris" inside "Val Parisis") were all treated
  equally.

This module centralises the two things that should behave identically
everywhere: **accent/case normalisation** and **match-quality scoring**. Each
endpoint keeps its own candidate query, marshalling and secondary sort (e.g.
by followers, or by administrative level for zones) and only borrows the
scoring from here.
"""

import re

from mongoengine.queryset.visitor import Q
from slugify import slugify

# Match-quality tiers, from best to worst. Lower sorts first.
EXACT = 0  # normalised name equals the query
PREFIX = 1  # normalised name starts with the query
WORD = 2  # query is a whole (hyphen-delimited) token inside the name
SUBSTRING = 3  # query appears somewhere in the name but not as a word
NO_MATCH = 4  # query is absent (should not happen for candidates)


def normalize(value: str) -> str:
    """Accent-insensitive, lowercased, hyphen-separated form used for matching.

    Relies on the same ``slugify`` already used by tags and users, so that
    "Orléans", "orleans" and "ORLEANS" all normalise to ``orleans``.
    """
    return slugify(value or "", separator="-", to_lower=True)


def match_score(text: str, query: str) -> int:
    """Rank how well ``text`` matches ``query``.

    Both sides are normalised, so matching is accent- and case-insensitive.
    Because :func:`normalize` joins tokens with ``-``, word boundaries are
    simply hyphens: "paris" is a whole word in ``le-grand-paris`` but only a
    substring of ``val-parisis``.
    """
    q = normalize(query)
    if not q:
        # An empty query matches everything equally; let the secondary sort decide.
        return EXACT
    t = normalize(text)
    if not t:
        return NO_MATCH
    if t == q:
        return EXACT
    if t.startswith(q):
        return PREFIX
    if re.search(r"(^|-)" + re.escape(q) + r"(-|$)", t):
        return WORD
    if q in t:
        return SUBSTRING
    return NO_MATCH


def best_match_score(texts, query: str, blend_popularity: bool = False) -> int:
    """Best (lowest) match score across several fields (e.g. name and acronym).

    When ``blend_popularity`` is set, prefix and whole-word matches are merged
    into a single bucket. This is meant for endpoints that pre-order candidates
    by popularity (e.g. ``-metrics.followers``): a canonical, much-followed
    whole-word match then wins over an obscure prefix match, instead of the
    stricter lexical order relegating it. Exact matches stay on top and mere
    substrings stay at the bottom.
    """
    best = min((match_score(text, query) for text in texts), default=NO_MATCH)
    if blend_popularity and best == WORD:
        return PREFIX
    return best


def suggestion_key(get_texts, query: str, secondary=None, blend_popularity: bool = False):
    """Build a ``sorted`` key: match quality first, then an endpoint-specific tie-break.

    ``get_texts`` returns the matchable string(s) of an item; ``secondary``
    (optional) returns a tuple used to order items of equal match quality
    (e.g. ``(LEVEL_PRIORITY[level], name)`` for zones, or ``-followers``).
    """

    def key(item):
        texts = get_texts(item)
        if isinstance(texts, str):
            texts = (texts,)
        score = (best_match_score(texts, query, blend_popularity),)
        if secondary is not None:
            extra = secondary(item)
            score += tuple(extra) if isinstance(extra, (tuple, list)) else (extra,)
        return score

    return key


def sorted_suggestions(items, query, get_texts, secondary=None, size=None, blend_popularity=False):
    """Sort candidate ``items`` by match quality then ``secondary``, capped at ``size``."""
    ordered = sorted(items, key=suggestion_key(get_texts, query, secondary, blend_popularity))
    return ordered[:size] if size is not None else ordered


# Upper bound on candidates fetched from MongoDB before Python re-ranking, so a
# common substring on a large collection does not pull the whole table.
DEFAULT_POOL = 200


def mongo_suggest(
    queryset,
    query,
    match_fields,
    size,
    slug_field=None,
    order_by=None,
    secondary=None,
    pool=DEFAULT_POOL,
    blend_popularity=False,
):
    """Fetch accent-aware candidates from ``queryset`` and rank them by match quality.

    - ``match_fields``: model fields matched with ``icontains`` (case-insensitive)
      and scored for match quality.
    - ``slug_field``: an already-normalised field (e.g. ``slug``) matched against
      the normalised query, so "orleans" retrieves "Orléans".
    - ``order_by``: a MongoDB ordering (e.g. ``-metrics.followers``) used to
      pre-order the fetched pool. Because the final Python sort is *stable*, items
      of equal match quality keep this order — so popularity ranking is preserved
      within each tier without an explicit ``secondary`` key.
    - ``secondary``: optional Python tie-break applied after match quality (used
      when there is no natural MongoDB pre-order).
    - ``blend_popularity``: merge prefix and whole-word matches into one bucket so
      the ``order_by`` popularity decides between them (see :func:`best_match_score`).
    """
    norm = normalize(query)

    conditions = None
    for field in match_fields:
        condition = Q(**{f"{field}__icontains": query})
        conditions = condition if conditions is None else conditions | condition
    if slug_field and norm:
        condition = Q(**{f"{slug_field}__icontains": norm})
        conditions = condition if conditions is None else conditions | condition

    candidates = queryset.filter(conditions) if conditions is not None else queryset
    if order_by:
        candidates = candidates.order_by(order_by)
    candidates = list(candidates.limit(pool))

    return sorted_suggestions(
        candidates,
        query,
        get_texts=lambda item: [getattr(item, field, None) for field in match_fields],
        secondary=secondary,
        size=size,
        blend_popularity=blend_popularity,
    )
