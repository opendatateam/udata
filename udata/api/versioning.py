from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypedDict

from flask import g, request
from packaging.version import InvalidVersion, Version

VERSION_HEADER = "X-API-Version"
LATEST_API_VERSION = Version("16.3.0")
OLDEST_API_VERSION = Version("1.0.0")


class VersionChangeInfo(TypedDict):
    version: str
    model: str
    field: str | None
    description: str


VERSION_CHANGES: list[VersionChangeInfo] = []


def get_request_version() -> Version:
    """Return the API version requested via header. Cached on flask.g."""
    if hasattr(g, "_api_version"):
        return g._api_version

    header = request.headers.get(VERSION_HEADER)
    if not header:
        version = OLDEST_API_VERSION
    else:
        try:
            version = Version(header)
        except InvalidVersion:
            from udata.api import api

            api.abort(400, f"Invalid {VERSION_HEADER} header. Expected a version like '16.3.0'.")

    g._api_version = version
    return version


@dataclass
class TransformEntry:
    func: Callable[[dict, Any, str], None]
    version: Version
    description: str


TRANSFORMS: dict[str, list[TransformEntry]] = {}


def version_transform(model_name: str, before: str, description: str = ""):
    """Register a version transform function.

    The decorated function receives (data, obj, context) where:
    - data: the already-marshalled dict (mutable)
    - obj: the original MongoEngine object
    - context: "read" for single objects, "page" for paginated items
    """
    ver = Version(before)

    def decorator(func):
        entry = TransformEntry(func=func, version=ver, description=description)
        TRANSFORMS.setdefault(model_name, []).append(entry)
        VERSION_CHANGES.append(
            {
                "version": before,
                "model": model_name,
                "field": None,
                "description": description,
            }
        )
        return func

    return decorator


def apply_transforms(model_name: str, data: dict, obj: Any, context: str, version: Version):
    """Apply all matching transforms for a model and version."""
    for entry in TRANSFORMS.get(model_name, []):
        if version < entry.version:
            entry.func(data, obj, context)
