"""Tools attached to the AI assistant agent.

`create_chart` and `update_chart` return dicts (validated chart or patch, or
a list of errors); the other tools return a French text. Outputs feed back
into the LLM as tool results, and error cases must be explained, never
raised — an exception escaping a tool kills the whole agent run.
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Annotated, Literal

from mongoengine.errors import DoesNotExist, ValidationError
from pydantic import Field
from pydantic_ai import Agent, RunContext

from udata.core.assistant.charts import (
    CreateChartInput,
    UpdateChartInput,
    profile_columns,
    query_aggregate_error,
    to_chart_output,
    to_update_output,
    validate_create,
    validate_update,
)
from udata.core.assistant.data_query import (
    PAGE_SIZE,
    Aggregate,
    GenericFilter,
    build_data_query,
    filter_columns,
    filter_errors,
    with_page,
)
from udata.core.assistant.tabular import TabularClient, TabularError, TabularRequestRefused
from udata.core.dataset.models import Dataset, Resource, get_dataset_by_resource_id
from udata.mongo.queryset import paginate_embedded_list

log = logging.getLogger(__name__)

# Per-turn budgets. Exhausted tool budgets return a refusal the model can
# explain; MODEL_REQUEST_LIMIT (passed as pydantic-ai usage limits) is the
# hard stop for a model that keeps calling tools after a refusal.
MAX_STEPS = 5
# Resources listed in a dataset's metadata, so a huge dataset cannot flood the context.
MAX_SERIALIZED_RESOURCES = 20
MAX_QUERIES_PER_QUESTION = 3
# One request per tool round, plus the refused round and the final answer.
MODEL_REQUEST_LIMIT = MAX_STEPS + 2


@dataclass
class AssistantDeps:
    """Per-turn state shared with the assistant agent.

    Tool calls run in a pydantic-ai worker thread that inherits the request
    context (contextvars), so permission checks use the requesting user's
    identity exactly like the rest of the API.
    """

    tabular: TabularClient
    resource_id: str | None = None
    tool_count: int = 0
    query_count: int = 0
    # Parallel tool calls run in separate threads: budgets are checked and spent atomically.
    budget_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)


def _consume_tool_budget(ctx: RunContext[AssistantDeps]) -> str | None:
    """Enforce MAX_STEPS as a per-turn tool-call cap.

    Returns a French refusal message once the budget is exhausted, None
    otherwise, so the model can still explain the limit in its answer.
    """
    with ctx.deps.budget_lock:
        if ctx.deps.tool_count >= MAX_STEPS:
            return (
                f"Action refusée : la limite de {MAX_STEPS} appels d'outils par tour est atteinte."
            )
        ctx.deps.tool_count += 1
    return None


def _consume_query_budget(ctx: RunContext[AssistantDeps]) -> str | None:
    """Enforce MAX_QUERIES_PER_QUESTION, returning a French refusal once it is exhausted."""
    with ctx.deps.budget_lock:
        if ctx.deps.query_count >= MAX_QUERIES_PER_QUESTION:
            return (
                f"Requête refusée : la limite de {MAX_QUERIES_PER_QUESTION} "
                "requêtes par question est atteinte."
            )
        ctx.deps.query_count += 1
    return None


def _dataset_for_current_user(dataset_id: str) -> Dataset | None:
    """Fetch a dataset the requesting user is allowed to read, else None.

    Hidden datasets (private, archived or deleted) are only exposed to their
    owner, their organization or an admin — the same OwnableReadPermission
    rule as the dataset API.
    """
    try:
        dataset = Dataset.objects.exclude("resources").get(id=dataset_id)
    except (DoesNotExist, ValidationError):
        return None
    if dataset.permissions["read"].can():
        return dataset
    return None


def _dataset_for_resource(resource_id: str) -> Dataset | None:
    """Owner dataset of a resource, readable by the requesting user, else None."""
    dataset = get_dataset_by_resource_id(resource_id, exclude_resources=True)
    if dataset is not None and dataset.permissions["read"].can():
        return dataset
    return None


def _render_profile(profile: dict) -> str:
    """Render the columns and line count of an api-tabular profile, whatever its shape."""
    columns = profile_columns(profile)
    lines = ["Colonnes :", *(f"- {name} ({kind})" for name, kind in columns.items())]
    if not columns:
        lines = ["Aucune information de colonne disponible."]
    details = profile.get("profile") if isinstance(profile, dict) else None
    total_lines = details.get("total_lines") if isinstance(details, dict) else None
    if isinstance(total_lines, int):
        lines.append(f"Nombre de lignes : {total_lines}")
    return "\n".join(lines)


def _render_result(result: dict) -> str:
    """Render the `data` rows of an api-tabular response as a pipe-separated table.

    A query without aggregate has an exact `meta.total`, which tells whether rows are cut.
    """
    rows = result.get("data") if isinstance(result, dict) else None
    rows = [row for row in rows or [] if isinstance(row, dict)]
    if not rows:
        return "Requête exécutée avec succès, aucune ligne retournée."
    meta = result.get("meta")
    total = meta.get("total") if isinstance(meta, dict) else None
    if not isinstance(total, int):
        total = len(rows)
    columns = list(rows[0])
    lines = [" | ".join(columns)]
    for row in rows[:PAGE_SIZE]:
        lines.append(" | ".join(str(row.get(column)) for column in columns))
    if total > min(len(rows), PAGE_SIZE):
        lines.append(
            f"Résultat tronqué : {total} lignes au total, {PAGE_SIZE} premières lignes affichées."
        )
    return "\n".join(lines)


NO_ACTIVE_RESOURCE = "Aucune ressource active : ouvrez une ressource dans le data studio."
RESOURCE_NOT_FOUND = (
    "Ressource introuvable : aucune ressource visible ne correspond à cet identifiant."
)
TABULAR_UNAVAILABLE = "Le service tabulaire est indisponible."


def _tabular_error_message(error: TabularError) -> str:
    """French message for the model; the English text of a TabularError is never forwarded."""
    if isinstance(error, TabularRequestRefused):
        return f"Requête refusée par le service tabulaire : {error.detail}."
    return TABULAR_UNAVAILABLE


def _active_columns(ctx: RunContext[AssistantDeps]) -> tuple[str, dict[str, str], dict]:
    """Active resource id, its profile columns and profile, or raise `_ToolRefusal`."""
    resource_id = ctx.deps.resource_id
    if not resource_id:
        raise _ToolRefusal(NO_ACTIVE_RESOURCE)
    if _dataset_for_resource(resource_id) is None:
        raise _ToolRefusal(RESOURCE_NOT_FOUND)
    try:
        profile = ctx.deps.tabular.get_profile(resource_id)
    except TabularError as error:
        raise _ToolRefusal(_tabular_error_message(error)) from error
    return resource_id, profile_columns(profile), profile


class _ToolRefusal(Exception):
    """Internal: a refusal message to hand back to the model, never escapes a tool."""


def _has_more_groups(tabular: TabularClient, resource_id: str, query: str, rows: list) -> bool:
    if len(rows) < PAGE_SIZE:
        return False
    return tabular.has_more_groups(resource_id, query)


def _distinct_groups(profile: dict, column: str) -> int | None:
    """Groups of the whole table grouped by `column`, from the profile statistics.

    One group per distinct value, plus one for the missing values.
    """
    details = profile.get("profile") if isinstance(profile, dict) else None
    stats = details.get("profile") if isinstance(details, dict) else None
    column_stats = stats.get(column) if isinstance(stats, dict) else None
    if not isinstance(column_stats, dict):
        return None
    distinct = column_stats.get("nb_distinct")
    if not isinstance(distinct, int):
        return None
    missing = column_stats.get("nb_missing_values")
    return distinct + (1 if isinstance(missing, int) and missing > 0 else 0)


def _chart_has_more_groups(
    tabular: TabularClient, resource_id: str, config: CreateChartInput, profile: dict
) -> bool:
    """Whether the viewer truncates a series to its first PAGE_SIZE rows.

    A series without aggregate returns rows, not groups: it is checked first, as
    the most likely to overflow, from its exact row count. An aggregated series
    has no total: without filter the profile counts its groups, otherwise page
    51 is probed. The checks stop at the first overflow or service failure.
    """
    x = config.x_axis.column_x
    unfiltered = not build_data_query(filters=config.filters)
    checked = set()
    try:
        for series in sorted(config.series, key=lambda series: series.aggregate_y is not None):
            aggregated = series.aggregate_y is not None
            query = build_data_query(
                # Like the viewer: grouped with an aggregate, the two raw columns without.
                columns=None if aggregated else [x, series.column_y],
                groupby=x if aggregated else None,
                aggregate=(series.column_y, series.aggregate_y) if aggregated else None,
                filters=config.filters,
                sort=(x, "asc"),
            )
            if query in checked:
                continue
            checked.add(query)
            if aggregated and unfiltered and (groups := _distinct_groups(profile, x)) is not None:
                overflow = groups > PAGE_SIZE
            elif not aggregated and (total := tabular.row_count(resource_id, query)) is not None:
                overflow = total > PAGE_SIZE
            else:
                overflow = tabular.has_more_groups(resource_id, query)
            if overflow:
                return True
    except TabularError:
        log.warning("Could not check the group count of a chart", exc_info=True)
    return False


def serialize_dataset_metadata(dataset: Dataset) -> str:
    """JSON metadata of a dataset loaded without its resources, listing the first ones only.

    Shared by the tool and the chat endpoint.
    """
    resources, total = paginate_embedded_list(
        Dataset, dataset.id, "resources", Resource, page=1, page_size=MAX_SERIALIZED_RESOURCES
    )
    payload = {
        "id": str(dataset.id),
        "title": dataset.title,
        "license": dataset.license.title if dataset.license else None,
        "organization": dataset.organization.name if dataset.organization else None,
        "resources": [
            {"id": str(resource.id), "title": resource.title, "format": resource.format}
            for resource in resources
        ],
    }
    if total > len(resources):
        payload["more_resources"] = f"… et {total - len(resources)} autres"
    return json.dumps(payload, ensure_ascii=False, indent=2)


def register_tools(agent: Agent) -> None:
    """Attach the assistant tools to a pydantic-ai agent."""

    @agent.tool
    def get_dataset_metadata(ctx: RunContext[AssistantDeps], dataset_id: str) -> str:
        """Récupère les métadonnées d'un dataset : titre, licence, organisation et ressources."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        dataset = _dataset_for_current_user(dataset_id)
        if dataset is None:
            return f"Dataset introuvable : aucun dataset ne correspond à « {dataset_id} »."
        return serialize_dataset_metadata(dataset)

    @agent.tool
    def inspect_schema(ctx: RunContext[AssistantDeps], resource_id: str) -> str:
        """Inspecte le schéma d'une ressource tabulaire : colonnes, types et nombre de lignes."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        if _dataset_for_resource(resource_id) is None:
            return RESOURCE_NOT_FOUND
        try:
            profile = ctx.deps.tabular.get_profile(resource_id)
        except TabularError as error:
            return _tabular_error_message(error)
        return _render_profile(profile)

    @agent.tool
    def query_data(
        ctx: RunContext[AssistantDeps],
        groupby: str | None = None,
        aggregate_column: str | None = None,
        aggregate: Aggregate | None = None,
        filters: GenericFilter | None = None,
        sort_column: str | None = None,
        sort_direction: Literal["asc", "desc"] = "asc",
        columns: list[str] | None = None,
    ) -> str:
        """Interroge la ressource active (lecture seule) pour vérifier les données avant un graphique.

        Un agrégat sans `groupby` est autorisé : il donne un total global.
        Pour regrouper, renseigne `groupby`, `aggregate_column` et `aggregate`
        (avg, sum, count, min, max). Sans tri explicite, un regroupement est trié
        sur la colonne de regroupement. Avec un agrégat, ne passe pas `columns` et ne
        trie que sur la colonne `groupby` (le service ne trie pas sur une valeur
        agrégée). Retourne au plus 50 lignes.
        """
        if refusal := _consume_tool_budget(ctx):
            return refusal
        if bool(aggregate_column) != bool(aggregate):
            return "Requête invalide : aggregate_column et aggregate vont ensemble."
        if groupby and not aggregate:
            return "Requête invalide : groupby demande un agrégat (aggregate_column et aggregate)."
        if aggregate and columns:
            return "Requête invalide : columns ne peut pas être combiné avec un agrégat ; retire columns."
        if aggregate and sort_column and sort_column != groupby:
            return (
                "Requête invalide : le tri n'est possible que sur la colonne groupby ; "
                "le service ne trie pas sur une valeur agrégée. "
                "Trie côté graphique avec sort_x_by=axis_y."
            )
        try:
            resource_id, known, _ = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return str(refusal)
        used = [groupby, aggregate_column, sort_column, *(columns or []), *filter_columns(filters)]
        unknown = list(dict.fromkeys(name for name in used if name and name not in known))
        if unknown:
            return "\n".join(f"Colonne inconnue : {name}." for name in unknown)
        refusals = filter_errors(filters)
        if aggregate and (
            error := query_aggregate_error(aggregate_column, aggregate, known[aggregate_column])
        ):
            refusals.append(error)
        if refusals:
            return "\n".join(refusals)
        if refusal := _consume_query_budget(ctx):
            return refusal
        sort = (sort_column, sort_direction) if sort_column else None
        if sort is None and groupby:
            sort = (groupby, "asc")
        query = build_data_query(
            groupby=groupby,
            aggregate=(aggregate_column, aggregate) if aggregate_column and aggregate else None,
            filters=filters,
            sort=sort,
            columns=columns,
        )
        try:
            result = ctx.deps.tabular.get_data(resource_id, with_page(query))
            rendered = _render_result(result)
            rows = result.get("data") if isinstance(result, dict) else None
            if groupby and _has_more_groups(ctx.deps.tabular, resource_id, query, rows or []):
                rendered += (
                    f"\nPlus de {PAGE_SIZE} groupes : seuls les {PAGE_SIZE} premiers "
                    "sont pris en compte."
                )
        except TabularError as error:
            return _tabular_error_message(error)
        return rendered

    @agent.tool
    def create_chart(ctx: RunContext[AssistantDeps], config: CreateChartInput) -> dict:
        """Crée un graphique sur la ressource active et remplace la structure du graphique en cours.

        À n'appeler qu'après une vérification avec `query_data`. Types : line ou
        histogram, 1 à 4 séries. Retourne le graphique validé ou la liste des erreurs
        à corriger.
        """
        if refusal := _consume_tool_budget(ctx):
            return {"status": "error", "errors": [refusal]}
        try:
            resource_id, known, profile = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return {"status": "error", "errors": [str(refusal)]}
        if errors := validate_create(config, known):
            return {"status": "error", "errors": errors}
        return {
            "status": "ok",
            "chart": to_chart_output(config, resource_id),
            "more_groups": _chart_has_more_groups(ctx.deps.tabular, resource_id, config, profile),
        }

    @agent.tool
    def update_chart(ctx: RunContext[AssistantDeps], patch: UpdateChartInput) -> dict:
        """Modifie la présentation du graphique en cours : titre, description, type, axe Y.

        Ne jamais l'utiliser pour changer les colonnes, les agrégats, les filtres
        ou l'axe X : utilise `create_chart` dans ce cas.
        """
        if refusal := _consume_tool_budget(ctx):
            return {"status": "error", "errors": [refusal]}
        if errors := validate_update(patch):
            return {"status": "error", "errors": errors}
        return {"status": "ok", "patch": to_update_output(patch)}

    @agent.tool
    def request_clarification(
        ctx: RunContext[AssistantDeps],
        question: str,
        choices: Annotated[list[str], Field(min_length=2, max_length=4)],
    ) -> str:
        """Demande une clarification à l'utilisateur en proposant une liste de choix numérotés."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        lines = [question, ""]
        for index, choice in enumerate(choices, start=1):
            lines.append(f"{index}. {choice}")
        return "\n".join(lines)
