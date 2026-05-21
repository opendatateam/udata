from udata.core.dataservices.openapi_filter import (
    FilterInfo,
    extract_filter_info,
    extract_indexable_text,
    matches_endpoint,
)

# --- extract_filter_info ---


def test_filter_info_non_bouquet_returns_none():
    assert extract_filter_info("API Geo") is None
    assert extract_filter_info("") is None
    assert extract_filter_info(None) is None


def test_filter_info_simple_bouquet():
    info = extract_filter_info("API Qualibat | Bouquet API Entreprise")
    assert info == FilterInfo(name="Qualibat", provider=None)


def test_filter_info_with_provider():
    info = extract_filter_info("API Liens de succession - Insee | Bouquet API Entreprise")
    assert info == FilterInfo(name="Liens de succession", provider="Insee")


def test_filter_info_provider_with_dash_in_name():
    info = extract_filter_info("API Foo - Bar - Acme | Bouquet API Entreprise")
    assert info == FilterInfo(name="Foo - Bar", provider="Acme")


# --- matches_endpoint ---


def test_matches_direct_substring():
    assert matches_endpoint(
        "Liens de succession",
        "/v3/insee/sirene/etablissements/{siret}/successions",
        FilterInfo(name="Liens de succession", provider="Insee"),
    )


def test_matches_normalizes_accents():
    assert matches_endpoint(
        "Données associations", "/some/path", FilterInfo(name="Donnees associations", provider=None)
    )


def test_matches_word_level():
    # Word-level match requires >=3 significant words (>2 chars) in the name.
    assert matches_endpoint(
        "Certificat carte travaux professionnelle publics délivré",
        "/x",
        FilterInfo(name="Carte professionnelle travaux publics", provider=None),
    )


def test_matches_provider_fallback():
    path = "/v3/fntp/unites_legales/{siren}/carte_professionnelle_travaux_publics"
    assert matches_endpoint(
        "Carte travaux publics professionnelle",
        path,
        FilterInfo(name="Carte professionnelle travaux", provider="FNTP"),
    )


def test_matches_no_match():
    assert not matches_endpoint(
        "Bilans financiers",
        "/v3/banque_de_france/bilans",
        FilterInfo(name="Liens de succession", provider="Insee"),
    )


# --- extract_indexable_text ---


SWAGGER = {
    "openapi": "3.0.1",
    "info": {
        "title": "API Entreprise",
        "description": "Bouquet of public-sector APIs",
    },
    "paths": {
        "/v3/insee/sirene/etablissements/{siret}/successions": {
            "get": {
                "summary": "Liens de succession",
                "description": "Liste des prédécesseurs et successeurs d'un établissement.",
                "tags": ["Insee"],
                "parameters": [
                    {"name": "siret", "in": "path", "description": "Siret de l'établissement"}
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Succession"}
                            }
                        },
                    }
                },
            }
        },
        "/v3/fntp/unites_legales/{siren}/carte_professionnelle_travaux_publics": {
            "get": {
                "summary": "Carte professionnelle travaux publics",
                "description": (
                    "Certificat indiquant qu'une entreprise de travaux publics affiliée à la FNTP."
                ),
                "tags": ["FNTP"],
                "responses": {"200": {"description": "OK"}},
            }
        },
    },
    "components": {
        "schemas": {
            "Succession": {
                "type": "object",
                "properties": {
                    "transfert_siege": {
                        "title": "Transfert de siège",
                        "description": "Indique si la succession est un transfert de siège",
                        "type": "boolean",
                    }
                },
            }
        }
    },
}


def test_extract_non_bouquet_indexes_everything():
    text = extract_indexable_text(SWAGGER, "API Entreprise")
    assert "Liens de succession" in text
    assert "Transfert de siège" in text
    assert "Carte professionnelle travaux publics" in text


def test_extract_bouquet_fiche_keeps_only_matching_path():
    text = extract_indexable_text(
        SWAGGER, "API Liens de succession - Insee | Bouquet API Entreprise"
    )
    assert "Liens de succession" in text
    assert "Transfert de siège" in text  # via $ref resolution
    assert "travaux publics" not in text


def test_extract_no_match_falls_back_to_all_paths():
    # "Qualibat" doesn't appear in any summary and FNTP provider only matches one path
    # by location but the name shares no words → no match → fallback returns everything.
    text = extract_indexable_text(SWAGGER, "API Qualibat - Acme | Bouquet API Entreprise")
    assert text is not None
    assert "Liens de succession" in text


def test_extract_info_block_included():
    text = extract_indexable_text(SWAGGER, "API Entreprise")
    assert "Bouquet of public-sector APIs" in text


def test_extract_path_tokens_included():
    text = extract_indexable_text(
        SWAGGER, "API Liens de succession - Insee | Bouquet API Entreprise"
    )
    assert "sirene" in text
    assert "successions" in text
    # Numeric/version segments like v3 must be dropped
    tokens = text.split()
    assert "v3" not in tokens


def test_extract_circular_ref_terminates():
    spec = {
        "openapi": "3.0.1",
        "paths": {
            "/x": {
                "get": {
                    "summary": "X endpoint",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/A"}}
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "properties": {"self": {"$ref": "#/components/schemas/A"}},
                },
            }
        },
    }
    text = extract_indexable_text(spec, "API Foo")
    assert "X endpoint" in text


def test_extract_returns_none_for_non_openapi():
    assert extract_indexable_text({"random": "json"}, "title") is None
    assert extract_indexable_text("not a dict", "title") is None
    assert extract_indexable_text(None, "title") is None
