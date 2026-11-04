"""Tools attached to the AI assistant agent.

Every tool returns a French text: outputs feed back into the LLM as tool
results, and error cases must be explained, never raised — an exception
escaping a tool kills the whole agent run.
"""

import json
from dataclasses import dataclass

from mongoengine.errors import DoesNotExist, ValidationError
from pydantic_ai import Agent, RunContext

from udata.core.assistant.tabular import TabularClient, TabularError
from udata.core.dataset.models import Dataset
from udata.sql_guard import UnsafeSQLError, assert_read_only

# Hard cap on rendered rows so huge results do not blow up the context window.
MAX_RENDERED_ROWS = 50
# Per-turn budgets. Exhausted tool budgets return a refusal the model can
# explain; MODEL_REQUEST_LIMIT (passed as pydantic-ai usage limits) is the
# hard stop for a model that keeps calling tools after a refusal.
MAX_STEPS = 5
MAX_SQL_PER_QUESTION = 3
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
    sql_count: int = 0
    tool_count: int = 0


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
    columns = profile.get("columns")
    if columns is None and isinstance(profile.get("profile"), dict):
        columns = [{"name": name, "type": type_} for name, type_ in profile["profile"].items()]
    lines = []
    if columns:
        lines.append("Colonnes :")
        for column in columns:
            lines.append(f"- {column.get('name', '?')} ({column.get('type', 'type inconnu')})")
    else:
        lines.append("Aucune information de colonne disponible.")
    nb_rows = profile.get("nb_rows") or profile.get("row_count")
    if nb_rows is not None:
        lines.append(f"Nombre de lignes : {nb_rows}")
    return "\n".join(lines)


def _render_result(result: dict) -> str:
    columns = result.get("columns") or []
    rows = result.get("rows") or []
    lines = []
    if columns:
        lines.append(" | ".join(str(column) for column in columns))
    for row in rows[:MAX_RENDERED_ROWS]:
        lines.append(" | ".join(str(value) for value in row))
    if len(rows) > MAX_RENDERED_ROWS:
        lines.append(
            f"Résultat tronqué : {len(rows)} lignes au total, "
            f"{MAX_RENDERED_ROWS} premières lignes affichées."
        )
    if not lines:
        return "Requête exécutée avec succès, aucune ligne retournée."
    return "\n".join(lines)


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
    """Attach the four assistant tools to a pydantic-ai agent."""

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
            return (
                "Ressource introuvable : aucune ressource visible ne correspond à cet identifiant."
            )
        try:
            profile = ctx.deps.tabular.get_profile(resource_id)
        except TabularError:
            return "Impossible d'inspecter le schéma de la ressource : le service tabulaire est indisponible."
        return _render_profile(profile)

    @agent.tool
    def execute_sql(ctx: RunContext[AssistantDeps], resource_id: str, sql: str) -> str:
        """Exécute une requête SQL en lecture seule sur une ressource tabulaire."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        if _dataset_for_resource(resource_id) is None:
            return (
                "Ressource introuvable : aucune ressource visible ne correspond à cet identifiant."
            )
        try:
            assert_read_only(sql)
        except UnsafeSQLError as error:
            # The guard's reason lets the model fix the query on its next try.
            return (
                "Requête refusée : l'assistant fonctionne en lecture seule "
                f"et cette requête n'est pas autorisée ({error})."
            )
        if ctx.deps.sql_count >= MAX_SQL_PER_QUESTION:
            return (
                f"Requête refusée : la limite de {MAX_SQL_PER_QUESTION} "
                "requêtes SQL par question est atteinte."
            )
        ctx.deps.sql_count += 1
        try:
            result = ctx.deps.tabular.execute_sql(resource_id, sql)
        except TabularError:
            return "L'exécution de la requête a échoué : le service tabulaire est indisponible."
        return _render_result(result)

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
