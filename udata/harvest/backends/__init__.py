from fnmatch import fnmatch
from importlib.metadata import entry_points

from flask import current_app

from .base import BaseBackend, HarvestExtraConfig, HarvestFeature, HarvestFilter  # noqa


def get_backend(name: str) -> type[BaseBackend] | None:
    return get_enabled_backends().get(name)


def get_all_backends() -> dict[str, type[BaseBackend]]:
    # Note that we use the `BaseBackend.name` and not `ep.name`. The entrypoint name
    # is not used anymore.
    return {ep.load().name: ep.load() for ep in entry_points(group="udata.harvesters")}


def is_backend_enabled(backend: type[BaseBackend]) -> bool:
    return any(fnmatch(backend.name, g) for g in current_app.config["HARVESTER_BACKENDS"])


def get_enabled_backends() -> dict[str, type[BaseBackend]]:
    return {
        name: backend for name, backend in get_all_backends().items() if is_backend_enabled(backend)
    }


def get_enabled_backends_ids() -> list[str]:
    # The enum= is API Fields is loaded before the current app require for
    # HARVESTER_BACKENDS so we need to defer it by having a function instead
    # of directly calling `get_enabled_backends().keys()`
    return list(get_enabled_backends().keys())
