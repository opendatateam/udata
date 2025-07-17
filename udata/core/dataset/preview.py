from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from flask import current_app

if TYPE_CHECKING:
    from udata.models import Resource


# Define an abstract class
class Preview(ABC):
    @abstractmethod
    def preview_url(self, resource: Resource) -> Optional[str]:
        return None


class TabularAPIPreview(Preview):
    def preview_url(self, resource: Resource) -> Optional[str]:
        preview_base_url = current_app.config["TABULAR_EXPLORE_URL"]
        if not preview_base_url:
            return None

        if "analysis:parsing:parsing_table" not in resource.extras:
            return None

        if resource.filetype == "remote" and not current_app.config["TABULAR_ALLOW_REMOTE"]:
            return None

        return f"{preview_base_url}/resources/{resource.id}"
