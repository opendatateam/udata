from fnmatch import fnmatch
from importlib.metadata import entry_points

from flask import current_app

from .base import BaseBackend, HarvestExtraConfig, HarvestFeature, HarvestFilter  # noqa


def get_backend(name: str) -> type[BaseBackend] | None:
    backend = get_enabled_backends().get(name)
    if not backend:
        raise ValueError(f"Backend {name} unknown. Make sure it is declared in HARVESTER_BACKENDS.")
    return backend


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
