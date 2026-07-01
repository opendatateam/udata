"""Lookup helpers around the public "Recherche d'entreprises" API.

Used to enrich an organization with administrative information derived from its
SIRET — currently the GeoZone of the French local authority (commune,
département, région, EPCI) the organization stands for.
"""

import logging

import requests
from flask import current_app

log = logging.getLogger(__name__)

# INSEE "catégorie juridique" → udata GeoZone level mapping.
# Full referential: https://www.insee.fr/fr/information/2028129
# Only entities whose geoid we can derive from the public Recherche d'entreprises
# payload are listed here; extend as we gain confidence in additional shapes.
NATURE_JURIDIQUE_TO_LEVEL: dict[str, str] = {
    "7210": "commune",  # Commune et commune nouvelle
    "7220": "departement",  # Département
    "7230": "region",  # Région
    "7340": "epci",  # Pôle métropolitain
    "7343": "epci",  # Communauté urbaine
    "7344": "epci",  # Métropole
    "7346": "epci",  # Communauté d'agglomération
    "7347": "epci",  # Communauté de communes
    "7348": "epci",  # Communauté ou syndicat d'agglomération nouvelle
}


def fetch_company_info(siret: str) -> dict | None:
    """Call the public "Recherche d'entreprises" search endpoint for one SIRET.

    Returns the matching company dict, or None when nothing actionable came back
    (API disabled, transient outage, malformed body, or no entity matching the
    queried SIRET). Callers should treat None as "do not change derived data".
    """
    base_url = current_app.config.get("RECHERCHE_ENTREPRISES_BASE_URL")
    if not base_url:
        return None
    timeout = current_app.config.get("RECHERCHE_ENTREPRISES_TIMEOUT", 5)
    try:
        response = requests.get(
            f"{base_url}/search",
            params={"q": siret, "page": 1, "per_page": 1},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log.warning("Recherche d'entreprises lookup failed for SIRET %s: %s", siret, exc)
        return None

    # `response.json()` raises `requests.exceptions.JSONDecodeError`, which inherits
    # from `ValueError` (and from `RequestException`). Catch it explicitly here so a
    # malformed body is logged distinctly from a network failure.
    try:
        payload = response.json()
    except ValueError:
        log.exception("Recherche d'entreprises returned invalid JSON for SIRET %s", siret)
        return None

    results = payload.get("results") if isinstance(payload, dict) else None
    if not results:
        return None
    top = results[0]
    # /search is a fuzzy, ranked endpoint: when no entity matches the queried
    # SIRET, it still returns its best guess. Confirm the queried SIRET maps to
    # one of the entity's establishments before trusting the result. Branches
    # (non-headquarters SIRETs) won't match `siege.siret` but should appear in
    # `matching_etablissements`.
    if not _siret_matches_entity(siret, top):
        log.info(
            "Recherche d'entreprises returned an entity (siren=%s) without %s in its "
            "establishments; ignoring",
            top.get("siren"),
            siret,
        )
        return None
    return top


def _siret_matches_entity(siret: str, entity: dict) -> bool:
    if siret == entity.get("siren"):  # caller queried with a SIREN
        return True
    siege_siret = (entity.get("siege") or {}).get("siret")
    if siret == siege_siret:
        return True
    for etab in entity.get("matching_etablissements") or []:
        if etab.get("siret") == siret:
            return True
    return False


def parse_zone_match(company_info: dict | None) -> tuple[str | None, str | None, bool]:
    """Inspect a company payload and report the GeoZone match decision.

    Returns ``(geoid_candidate, code, decisive)`` where:

    * ``decisive`` is False when the payload is too partial to act on (missing
      ``nature_juridique`` or the expected code for the level). The caller
      should preserve any existing derived data.
    * ``decisive`` is True with ``geoid_candidate=None`` means the legal entity
      is positively not a local authority we map to a GeoZone (private company,
      association, foreign entity, …). The caller may clear previously-derived
      data.
    * ``decisive`` is True with a non-None ``geoid_candidate`` means a match;
      the caller still needs to verify the GeoZone exists locally.
    """
    if not company_info or not company_info.get("nature_juridique"):
        return None, None, False
    nature_juridique = company_info["nature_juridique"]
    level = NATURE_JURIDIQUE_TO_LEVEL.get(nature_juridique)
    if level is None:
        # NATURE_JURIDIQUE_TO_LEVEL is deliberately partial: it only lists the
        # families whose geoid we can currently derive. The INSEE "7" family
        # (personnes morales de droit administratif) also covers collectivités
        # and public establishments we don't map yet — syndicats mixtes (7354),
        # régions/EPCI variants, CCAS, … — which may legitimately be local
        # authorities. Stay inconclusive there so we never erase a correct zone
        # just because the map is incomplete. Any other family (société,
        # association, entité étrangère, …) is positively not a French local
        # authority and may clear previously-derived data.
        if nature_juridique.startswith("7"):
            return None, None, False
        return None, None, True
    code = _code_for_level(level, company_info)
    if not code:
        # Payload announces a local-authority entity but lacks the expected
        # code — treat as inconclusive rather than clear.
        return None, None, False
    # `code_insee` is meant to carry an INSEE geographic code. An EPCI geoid is
    # keyed by the entity SIREN (see _code_for_level), which is not an INSEE
    # code, so don't expose it as one — set the zone but leave code_insee empty.
    code_insee = None if level == "epci" else code
    return f"fr:{level}:{code}", code_insee, True


def _code_for_level(level: str, company_info: dict) -> str | None:
    siege = company_info.get("siege") or {}
    if level == "commune":
        return siege.get("code_commune")
    if level == "departement":
        return siege.get("departement")
    if level == "region":
        return siege.get("region")
    if level == "epci":
        # The "conseil" of an EPCI is registered under the EPCI's own SIREN, so
        # the entity SIREN is the EPCI code used in `fr:epci:<siren>` geoids.
        return company_info.get("siren")
    return None
