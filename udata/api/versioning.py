from __future__ import annotations

from packaging.version import Version

from flask import g, request

VERSION_HEADER = "X-API-Version"
LATEST_API_VERSION = Version("16.3.0")
OLDEST_API_VERSION = Version("1.0.0")

# Registry of all version changes, populated at import time via change classes
VERSION_CHANGES: list[dict] = []


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
        except Exception:
            from udata.api import api

            api.abort(
                400, f"Invalid {VERSION_HEADER} header. Expected a version like '16.3.0'."
            )

    g._api_version = version
    return version


class VersionChange:
    """Base class for API version changes."""

    def __init__(self, version: str, description: str | None = None):
        self.version_str = version
        self.version = Version(version)
        self.description = description

    def auto_description(self) -> str:
        raise NotImplementedError

    def register(self, model_name: str, field_name: str | None = None):
        VERSION_CHANGES.append(
            {
                "version": self.version_str,
                "model": model_name,
                "field": field_name,
                "description": self.description or self.auto_description(),
            }
        )


class ChangeAttribute(VersionChange):
    """Before this version, some field attributes were different.

    Usage:
        datasets = field(
            ListField(...),
            href=lambda reuse: url_for(...),
            before=[
                ChangeAttribute("16.3.0", href=None,
                    description="datasets returned inline instead of href"),
            ],
        )
    """

    def __init__(self, version: str, description: str | None = None, **attrs):
        super().__init__(version, description)
        self.attrs = attrs

    def auto_description(self) -> str:
        changes = ", ".join(f"{k}={v!r}" for k, v in self.attrs.items())
        return f"Field attributes changed: {changes}"

    def apply(self, info: dict) -> dict:
        modified = {**info}
        modified.update(self.attrs)
        return modified


class RenameField(VersionChange):
    """Before this version, this field had a different name.

    Usage:
        new_name = field(
            StringField(),
            before=[
                RenameField("16.3.0", old_name="old_name"),
            ],
        )
    """

    def __init__(self, version: str, old_name: str, description: str | None = None):
        super().__init__(version, description)
        self.old_name = old_name

    def auto_description(self) -> str:
        return f"Field renamed from '{self.old_name}'"


class RemoveField(VersionChange):
    """At this version, this field was removed. Before this version it existed.

    Usage:
        legacy_field = field(
            StringField(),
            before=[
                RemoveField("16.3.0",
                    description="legacy_field has been removed"),
            ],
        )
    """

    def auto_description(self) -> str:
        return "Field removed"


class ChangeModelAttribute(VersionChange):
    """Before this version, model-level attributes (masks, etc.) were different.

    Usage:
        @generate_fields(
            before=[
                ChangeModelAttribute("16.3.0",
                    page_mask="*,datasets{id,title,uri,page}"),
            ],
        )
    """

    def __init__(self, version: str, description: str | None = None, **attrs):
        super().__init__(version, description)
        self.attrs = attrs

    def auto_description(self) -> str:
        changes = ", ".join(f"{k}={v!r}" for k, v in self.attrs.items())
        return f"Model attributes changed: {changes}"

    def apply(self, model_kwargs: dict) -> dict:
        modified = {**model_kwargs}
        modified.update(self.attrs)
        return modified
