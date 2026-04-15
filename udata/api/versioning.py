from __future__ import annotations

from datetime import date

from flask import g, request

VERSION_HEADER = "X-API-Version"
LATEST_API_VERSION = date(2026, 4, 15)
OLDEST_API_VERSION = date(2026, 4, 14)

# Registry of all version changes, populated at import time via change classes
VERSION_CHANGES: list[dict] = []


def get_request_version() -> date:
    """Return the API version requested via header. Cached on flask.g."""
    if hasattr(g, "_api_version"):
        return g._api_version

    header = request.headers.get(VERSION_HEADER)
    if not header:
        version = OLDEST_API_VERSION
    else:
        try:
            version = date.fromisoformat(header)
        except ValueError:
            from udata.api import api

            api.abort(400, f"Invalid {VERSION_HEADER} header. Expected YYYY-MM-DD format.")

    g._api_version = version
    return version


class VersionChange:
    """Base class for API version changes."""

    def __init__(self, version_date: str, description: str | None = None):
        self.version_date = version_date
        self.date = date.fromisoformat(version_date)
        self.description = description

    def auto_description(self) -> str:
        raise NotImplementedError

    def register(self, model_name: str, field_name: str | None = None):
        VERSION_CHANGES.append(
            {
                "date": self.version_date,
                "model": model_name,
                "field": field_name,
                "description": self.description or self.auto_description(),
            }
        )


class ChangeAttribute(VersionChange):
    """Before this date, some field attributes were different.

    Usage:
        datasets = field(
            ListField(...),
            href=lambda reuse: url_for(...),
            before=[
                ChangeAttribute("2026-04-15", href=None,
                    description="datasets returned inline instead of href"),
            ],
        )
    """

    def __init__(self, version_date: str, description: str | None = None, **attrs):
        super().__init__(version_date, description)
        self.attrs = attrs

    def auto_description(self) -> str:
        changes = ", ".join(f"{k}={v!r}" for k, v in self.attrs.items())
        return f"Field attributes changed: {changes}"

    def apply(self, info: dict) -> dict:
        modified = {**info}
        modified.update(self.attrs)
        return modified


class RenameField(VersionChange):
    """Before this date, this field had a different name.

    Usage:
        new_name = field(
            StringField(),
            before=[
                RenameField("2026-04-15", old_name="old_name"),
            ],
        )
    """

    def __init__(self, version_date: str, old_name: str, description: str | None = None):
        super().__init__(version_date, description)
        self.old_name = old_name

    def auto_description(self) -> str:
        return f"Field renamed from '{self.old_name}'"


class RemoveField(VersionChange):
    """At this date, this field was removed. Before this date it existed.

    Usage:
        legacy_field = field(
            StringField(),
            before=[
                RemoveField("2026-04-15",
                    description="legacy_field has been removed"),
            ],
        )
    """

    def auto_description(self) -> str:
        return "Field removed"


class ChangeModelAttribute(VersionChange):
    """Before this date, model-level attributes (masks, etc.) were different.

    Usage:
        @generate_fields(
            page_mask_exclude=["datasets"],
            before=[
                ChangeModelAttribute("2026-04-15",
                    page_mask="*,datasets{id,title,uri,page}"),
            ],
        )
    """

    def __init__(self, version_date: str, description: str | None = None, **attrs):
        super().__init__(version_date, description)
        self.attrs = attrs

    def auto_description(self) -> str:
        changes = ", ".join(f"{k}={v!r}" for k, v in self.attrs.items())
        return f"Model attributes changed: {changes}"

    def apply(self, model_kwargs: dict) -> dict:
        modified = {**model_kwargs}
        modified.update(self.attrs)
        return modified
