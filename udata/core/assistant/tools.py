"""Tools attached to the AI assistant agent.

Every tool returns a French text: outputs feed back into the LLM as tool
results, and error cases must be explained, never raised — an exception
escaping a tool kills the whole agent run.
"""

import json
from dataclasses import dataclass

from flask import current_app
from mongoengine.errors import DoesNotExist, ValidationError
from pydantic_ai import Agent, RunContext

from udata.core.assistant.sql_guard import UnsafeSQLError, assert_read_only
from udata.core.assistant.tabular import TabularClient, TabularError
from udata.core.dataset.models import Dataset

# Hard cap on rendered rows so huge results do not blow up the context window.
MAX_RENDERED_ROWS = 50


@dataclass
class AssistantDeps:
    """Per-turn state shared with the assistant agent."""

    tabular: TabularClient
    sql_count: int = 0
    tool_count: int = 0


def _max_sql_per_question() -> int:
    return current_app.config["AI_MAX_SQL_PER_QUESTION"]


def _consume_tool_budget(ctx: RunContext[AssistantDeps]) -> str | None:
    """Enforce AI_MAX_STEPS as a per-turn tool-call cap.

    pydantic-ai v2 has no step-cap parameter, so the step budget is proxied
    by counting tool calls per agent run. Returns a French refusal message
    once the budget is exhausted, None otherwise.
    """
    limit = current_app.config["AI_MAX_STEPS"]
    if ctx.deps.tool_count >= limit:
        return f"Action refusée : la limite de {limit} appels d'outils par tour est atteinte."
    ctx.deps.tool_count += 1
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
        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except (DoesNotExist, ValidationError):
            return f"Dataset introuvable : aucun dataset ne correspond à « {dataset_id} »."
        return serialize_dataset_metadata(dataset)

    @agent.tool
    def inspect_schema(ctx: RunContext[AssistantDeps], resource_id: str) -> str:
        """Inspecte le schéma d'une ressource tabulaire : colonnes, types et nombre de lignes."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        try:
            profile = ctx.deps.tabular.get_profile(resource_id)
        except TabularError as error:
            return f"Impossible d'inspecter le schéma de la ressource : {error}"
        return _render_profile(profile)

    @agent.tool
    def execute_sql(ctx: RunContext[AssistantDeps], resource_id: str, sql: str) -> str:
        """Exécute une requête SQL en lecture seule sur une ressource tabulaire."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        try:
            assert_read_only(sql)
        except UnsafeSQLError:
            return (
                "Requête refusée : l'assistant fonctionne en lecture seule "
                "et cette requête n'est pas autorisée."
            )
        limit = _max_sql_per_question()
        if ctx.deps.sql_count >= limit:
            return f"Requête refusée : la limite de {limit} requêtes SQL par question est atteinte."
        ctx.deps.sql_count += 1
        try:
            result = ctx.deps.tabular.execute_sql(resource_id, sql)
        except TabularError as error:
            return f"L'exécution de la requête a échoué : {error}"
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
