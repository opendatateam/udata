"""Tools attached to the AI assistant agent.

Every tool returns a French text: outputs feed back into the LLM as tool
results, and error cases must be explained, never raised — an exception
escaping a tool kills the whole agent run.
"""

import json
import logging
from dataclasses import dataclass
from typing import Literal

from mongoengine.errors import DoesNotExist, ValidationError
from pydantic_ai import Agent, RunContext

from udata.core.assistant.charts import (
    CreateChartInput,
    UpdateChartInput,
    profile_columns,
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
    with_page,
)
from udata.core.assistant.tabular import TabularClient, TabularError, TabularRequestRefused
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)

# Hard cap on rendered rows so huge results do not blow up the context window.
MAX_RENDERED_ROWS = 50
# Per-turn budgets. Exhausted tool budgets return a refusal the model can
# explain; MODEL_REQUEST_LIMIT (passed as pydantic-ai usage limits) is the
# hard stop for a model that keeps calling tools after a refusal.
MAX_STEPS = 5
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


def _consume_tool_budget(ctx: RunContext[AssistantDeps]) -> str | None:
    """Enforce MAX_STEPS as a per-turn tool-call cap.

    Returns a French refusal message once the budget is exhausted, None
    otherwise, so the model can still explain the limit in its answer.
    """
    if ctx.deps.tool_count >= MAX_STEPS:
        return f"Action refusée : la limite de {MAX_STEPS} appels d'outils par tour est atteinte."
    ctx.deps.tool_count += 1
    return None


def _dataset_for_current_user(dataset_id: str) -> Dataset | None:
    """Fetch a dataset the requesting user is allowed to read, else None.

    Hidden datasets (private, archived or deleted) are only exposed to their
    owner, their organization or an admin — the same OwnableReadPermission
    rule as the dataset API.
    """
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except (DoesNotExist, ValidationError):
        return None
    if dataset.permissions["read"].can():
        return dataset
    return None


def _dataset_for_resource(resource_id: str) -> Dataset | None:
    """Owner dataset of a resource, readable by the requesting user, else None."""
    dataset = Dataset.objects(resources__id=resource_id).first()
    if dataset is not None and dataset.permissions["read"].can():
        return dataset
    return None


def _render_profile(profile: dict) -> str:
    """Render an api-tabular profile: {"profile": {"header", "columns", "total_lines"}}."""
    details = profile.get("profile") if isinstance(profile.get("profile"), dict) else {}
    columns = details.get("columns") if isinstance(details.get("columns"), dict) else {}
    names = details.get("header") or list(columns)
    lines = []
    if names:
        lines.append("Colonnes :")
        for name in names:
            column = columns.get(name) or {}
            lines.append(f"- {name} ({column.get('python_type') or 'type inconnu'})")
    else:
        lines.append("Aucune information de colonne disponible.")
    total_lines = details.get("total_lines")
    if total_lines is not None:
        lines.append(f"Nombre de lignes : {total_lines}")
    return "\n".join(lines)


def _render_result(result: dict) -> str:
    """Render the `data` rows of an api-tabular response as a pipe-separated table."""
    rows = result.get("data") if isinstance(result, dict) else None
    rows = [row for row in rows or [] if isinstance(row, dict)]
    if not rows:
        return "Requête exécutée avec succès, aucune ligne retournée."
    columns = list(rows[0])
    lines = [" | ".join(columns)]
    for row in rows[:MAX_RENDERED_ROWS]:
        lines.append(" | ".join(str(row.get(column)) for column in columns))
    if len(rows) > MAX_RENDERED_ROWS:
        lines.append(
            f"Résultat tronqué : {len(rows)} lignes au total, "
            f"{MAX_RENDERED_ROWS} premières lignes affichées."
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


def _active_columns(ctx: RunContext[AssistantDeps]) -> tuple[str, dict[str, str]]:
    """Active resource id and its profile columns, or raise `_ToolRefusal` with the message."""
    resource_id = ctx.deps.resource_id
    if not resource_id:
        raise _ToolRefusal(NO_ACTIVE_RESOURCE)
    if _dataset_for_resource(resource_id) is None:
        raise _ToolRefusal(RESOURCE_NOT_FOUND)
    try:
        profile = ctx.deps.tabular.get_profile(resource_id)
    except TabularError as error:
        raise _ToolRefusal(_tabular_error_message(error)) from error
    return resource_id, profile_columns(profile)


class _ToolRefusal(Exception):
    """Internal: a refusal message to hand back to the model, never escapes a tool."""


def _has_more_groups(tabular: TabularClient, resource_id: str, query: str, rows: list) -> bool:
    if len(rows) < PAGE_SIZE:
        return False
    return tabular.has_more_groups(resource_id, query)


def serialize_dataset_metadata(dataset: Dataset) -> str:
    """JSON serialization of a dataset's metadata, shared by the tool and the chat endpoint."""
    payload = {
        "id": str(dataset.id),
        "title": dataset.title,
        "license": dataset.license.title if dataset.license else None,
        "organization": dataset.organization.name if dataset.organization else None,
        "resources": [
            {"id": str(resource.id), "title": resource.title, "format": resource.format}
            for resource in dataset.resources
        ],
    }
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
        sur la colonne de regroupement. Retourne au plus 50 lignes.
        """
        if refusal := _consume_tool_budget(ctx):
            return refusal
        try:
            resource_id, known = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return str(refusal)
        if bool(aggregate_column) != bool(aggregate):
            return "Requête invalide : aggregate_column et aggregate vont ensemble."
        if groupby and not aggregate:
            return "Requête invalide : groupby demande un agrégat (aggregate_column et aggregate)."
        used = [groupby, aggregate_column, sort_column, *(columns or []), *filter_columns(filters)]
        unknown = list(dict.fromkeys(name for name in used if name and name not in known))
        if unknown:
            return "\n".join(f"Colonne inconnue : {name}." for name in unknown)
        if ctx.deps.query_count >= MAX_QUERIES_PER_QUESTION:
            return (
                f"Requête refusée : la limite de {MAX_QUERIES_PER_QUESTION} "
                "requêtes par question est atteinte."
            )
        ctx.deps.query_count += 1
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
            resource_id, known = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return {"status": "error", "errors": [str(refusal)]}
        if errors := validate_create(config, known):
            return {"status": "error", "errors": errors}
        first = config.series[0]
        query = build_data_query(
            groupby=config.x_axis.column_x,
            aggregate=(first.column_y, first.aggregate_y) if first.aggregate_y else None,
            filters=config.filters,
            sort=(config.x_axis.column_x, "asc"),
        )
        more_groups = False
        try:
            result = ctx.deps.tabular.get_data(resource_id, with_page(query))
            rows = result.get("data") if isinstance(result, dict) else None
            more_groups = _has_more_groups(ctx.deps.tabular, resource_id, query, rows or [])
        except TabularError:
            log.warning("Could not check the group count of a chart", exc_info=True)
        return {
            "status": "ok",
            "chart": to_chart_output(config, resource_id),
            "more_groups": more_groups,
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
        ctx: RunContext[AssistantDeps], question: str, choices: list[str]
    ) -> str:
        """Demande une clarification à l'utilisateur en proposant une liste de choix numérotés."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        lines = [question, ""]
        for index, choice in enumerate(choices, start=1):
            lines.append(f"{index}. {choice}")
        return "\n".join(lines)
