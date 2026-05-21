"""
OpenAPI swagger parsing for search indexation.

For bouquet dataservices that share one swagger across many fiches, only the
endpoints whose operation summary matches the fiche title are kept — same
logic as `cdata/utils/openapi-bouquet.ts` so search and frontend agree.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, NamedTuple

METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

_BOUQUET_MARKER = "| Bouquet"

_TEXT_KEYS = ("title", "summary", "description")

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_PATH_SPLIT_RE = re.compile(r"[/_\-.]")
_VERSION_SEGMENT_RE = re.compile(r"v?\d+")


class FilterInfo(NamedTuple):
    name: str
    provider: str | None


# --- title parsing & endpoint matching ---


def _normalize(s: str) -> str:
    """Lowercase, strip accents (NFD), collapse whitespace."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _WHITESPACE_RE.sub(" ", s.lower()).strip()


def _normalize_words(s: str) -> list[str]:
    """Tokenize a normalized string into significant words (len > 2)."""
    norm = _NON_ALNUM_RE.sub(" ", _normalize(s))
    return [w for w in norm.split() if len(w) > 2]


def extract_filter_info(title: str | None) -> FilterInfo | None:
    """
    Parse a bouquet dataservice title into name + optional provider.

    Returns None if the title doesn't look like a bouquet fiche.

    Examples:
        "API Liens de succession - Insee | Bouquet API Entreprise"
          -> FilterInfo(name="Liens de succession", provider="Insee")
        "API Qualibat | Bouquet API Entreprise"
          -> FilterInfo(name="Qualibat", provider=None)
    """
    if not title or _BOUQUET_MARKER not in title:
        return None

    name = title.split(_BOUQUET_MARKER, 1)[0].strip()
    if name.startswith("API "):
        name = name[4:]

    provider: str | None = None
    if " - " in name:
        parts = name.split(" - ")
        provider = parts.pop().strip()
        name = " - ".join(parts).strip()

    return FilterInfo(name=name, provider=provider)


def matches_endpoint(summary: str, path: str, filter_info: FilterInfo) -> bool:
    """
    Return True if the given operation summary/path should be kept for a fiche.

    Three strategies, in order:
      1. Direct substring match (normalized) between summary and name.
      2. Word-level match: all significant words in name appear in summary words.
      3. Provider fallback: provider appears in path AND ≥2 long words shared.
    """
    norm_summary = _normalize(summary)
    norm_name = _normalize(filter_info.name)

    if norm_name and (norm_name in norm_summary or norm_summary in norm_name):
        return True

    name_words = _normalize_words(filter_info.name)
    summary_words = _normalize_words(summary)
    if len(name_words) >= 3 and all(
        any(w in sw or sw in w for sw in summary_words) for w in name_words
    ):
        return True

    provider = filter_info.provider
    if provider and _normalize(provider) in _normalize(path):
        common = [w for w in name_words if len(w) > 3 and any(w in sw for sw in summary_words)]
        if len(common) >= 2:
            return True

    return False


# --- schema resolution ---


def _is_obj(v: Any) -> bool:
    return isinstance(v, dict)


def _lookup_ref(ref: str, root: dict) -> dict | None:
    """Resolve an internal $ref like #/components/schemas/X. Returns None for external refs."""
    if not ref.startswith("#/"):
        return None
    node: Any = root
    for part in ref[2:].split("/"):
        if not _is_obj(node):
            return None
        node = node.get(part)
    return node if _is_obj(node) else None


# --- text extraction ---


def _walk_collect(node: Any, root: dict, out: list[str], seen: set[str]) -> None:
    """Walk an OpenAPI subtree, resolve $ref, collect indexable strings."""
    if _is_obj(node):
        ref = node.get("$ref")
        if isinstance(ref, str):
            if not ref.startswith("#/") or ref in seen:
                return
            target = _lookup_ref(ref, root)
            if target is not None:
                seen.add(ref)
                _walk_collect(target, root, out, seen)
                seen.discard(ref)
            return
        for k, v in node.items():
            if k in _TEXT_KEYS and isinstance(v, str) and v.strip():
                out.append(v.strip())
            elif isinstance(v, (dict, list)):
                _walk_collect(v, root, out, seen)
    elif isinstance(node, list):
        for item in node:
            _walk_collect(item, root, out, seen)


def _path_tokens(path: str) -> list[str]:
    """Tokenize an OpenAPI path, dropping placeholders and numeric/version-only segments."""
    tokens: list[str] = []
    for raw in _PATH_SPLIT_RE.split(path):
        if not raw or raw.startswith("{") or _VERSION_SEGMENT_RE.fullmatch(raw):
            continue
        tokens.append(raw.lower())
    return tokens


def _operation_texts(operation: dict, root: dict, path: str) -> list[str]:
    """Collect indexable text from an operation: summary/description/tags + parameters + bodies."""
    texts: list[str] = []

    for k in ("summary", "description"):
        v = operation.get(k)
        if isinstance(v, str) and v.strip():
            texts.append(v.strip())

    tags = operation.get("tags")
    if isinstance(tags, list):
        texts.extend(t.strip() for t in tags if isinstance(t, str) and t.strip())

    for param in operation.get("parameters") or []:
        _walk_collect(param, root, texts, set())

    body = operation.get("requestBody")
    if body is not None:
        _walk_collect(body, root, texts, set())

    responses = operation.get("responses")
    if _is_obj(responses):
        for resp in responses.values():
            _walk_collect(resp, root, texts, set())

    texts.extend(_path_tokens(path))
    return texts


def extract_indexable_text(spec: Any, title: str | None) -> str | None:
    """
    Walk an OpenAPI spec and return a single string of indexable text.

    For bouquet fiches, keeps only endpoints whose operation summary matches
    the fiche name. For non-bouquet fiches or when no endpoint matches in a
    bouquet, keeps everything.

    Returns None if the spec doesn't look like OpenAPI.
    """
    if not _is_obj(spec):
        return None
    paths = spec.get("paths")
    if not _is_obj(paths):
        return None

    pieces: list[str] = []

    info = spec.get("info")
    if _is_obj(info):
        for k in ("title", "description"):
            v = info.get(k)
            if isinstance(v, str) and v.strip():
                pieces.append(v.strip())

    filter_info = extract_filter_info(title)

    kept_paths: set[str] | None = None
    if filter_info:
        matched: set[str] = set()
        for path, item in paths.items():
            if not _is_obj(item):
                continue
            for method in METHODS:
                op = item.get(method)
                if not _is_obj(op):
                    continue
                if matches_endpoint(op.get("summary") or "", path, filter_info):
                    matched.add(path)
                    break
        # Fall back to all paths if filtering matched nothing — better to over-index
        # than to silently drop a fiche whose title doesn't fit the heuristic.
        kept_paths = matched or None

    for path, item in paths.items():
        if kept_paths is not None and path not in kept_paths:
            continue
        if not _is_obj(item):
            continue
        for method in METHODS:
            op = item.get(method)
            if _is_obj(op):
                pieces.extend(_operation_texts(op, spec, path))

    if not pieces:
        return None

    return " ".join(dict.fromkeys(pieces))
