from unittest.mock import MagicMock, patch

import pytest
import requests

from udata.core.organization.api_entreprise import parse_zone_match
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.tasks import lookup_organization_zone
from udata.core.spatial.factories import GeoZoneFactory
from udata.models import Organization
from udata.tests.api import PytestOnlyDBTestCase


class ParseZoneMatchTest:
    def test_decisive_match_for_commune(self):
        info = {
            "siren": "217500016",
            "nature_juridique": "7210",
            "siege": {"code_commune": "75056", "departement": "75", "region": "11"},
        }
        assert parse_zone_match(info) == ("fr:commune:75056", "75056", True)

    def test_decisive_match_for_departement(self):
        info = {
            "siren": "221300017",
            "nature_juridique": "7220",
            "siege": {"code_commune": "13201", "departement": "13", "region": "93"},
        }
        assert parse_zone_match(info) == ("fr:departement:13", "13", True)

    def test_decisive_match_for_region(self):
        info = {
            "siren": "231100018",
            "nature_juridique": "7230",
            "siege": {"code_commune": "75056", "departement": "75", "region": "11"},
        }
        assert parse_zone_match(info) == ("fr:region:11", "11", True)

    def test_decisive_match_for_epci_metropole(self):
        # The geoid is keyed by the entity SIREN, but that SIREN is not an INSEE
        # geographic code, so code_insee stays None for an EPCI.
        info = {
            "siren": "200054781",
            "nature_juridique": "7344",  # Métropole
            "siege": {"code_commune": "69266", "departement": "69", "region": "84"},
        }
        assert parse_zone_match(info) == ("fr:epci:200054781", None, True)

    def test_decisive_non_collectivite(self):
        info = {
            "siren": "552032534",
            "nature_juridique": "5710",  # SAS
            "siege": {"code_commune": "75056"},
        }
        assert parse_zone_match(info) == (None, None, True)

    def test_indecisive_for_unmapped_public_law_entity(self):
        """A "7" family category we don't map yet (e.g. syndicat mixte) may be a
        genuine local authority, so stay inconclusive rather than clear."""
        info = {
            "siren": "200054781",
            "nature_juridique": "7354",  # Syndicat mixte fermé — not in the map
            "siege": {"code_commune": "69266", "departement": "69", "region": "84"},
        }
        assert parse_zone_match(info) == (None, None, False)

    def test_indecisive_when_expected_code_missing(self):
        """Local-authority entity with no usable code → preserve."""
        # A département payload without the `departement` field is malformed.
        info = {"nature_juridique": "7220", "siege": {"code_commune": "13201"}}
        assert parse_zone_match(info) == (None, None, False)

    def test_indecisive_for_empty_input(self):
        assert parse_zone_match(None) == (None, None, False)
        assert parse_zone_match({}) == (None, None, False)
        assert parse_zone_match({"siege": {"code_commune": "75056"}}) == (None, None, False)


def _mock_search_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


def _commune_result(siret, code_commune):
    return {
        "results": [
            {
                "siren": siret[:9],
                "nature_juridique": "7210",
                "siege": {"siret": siret, "code_commune": code_commune},
                "matching_etablissements": [{"siret": siret}],
            }
        ]
    }


def _departement_result(siret, code_departement):
    return {
        "results": [
            {
                "siren": siret[:9],
                "nature_juridique": "7220",
                "siege": {"siret": siret, "departement": code_departement},
                "matching_etablissements": [{"siret": siret}],
            }
        ]
    }


def _non_collectivite_result(siret, nature_juridique="5710"):
    return {
        "results": [
            {
                "siren": siret[:9],
                "nature_juridique": nature_juridique,
                "siege": {"siret": siret},
                "matching_etablissements": [{"siret": siret}],
            }
        ]
    }


@pytest.mark.options(
    ORG_BID_FORMAT="siret",
    RECHERCHE_ENTREPRISES_BASE_URL="https://recherche-entreprises.api.gouv.fr",
)
class LookupOrganizationZoneTaskTest(PytestOnlyDBTestCase):
    SIRET = "21750055200012"  # Mairie de Paris (SIRET valide Luhn)
    OTHER_SIRET = "21750055299999"  # same valid SIREN, different NIC

    def _paris_zone(self):
        return GeoZoneFactory(id="fr:commune:75056", level="fr:commune", name="Paris", code="75056")

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_assigns_zone_and_code_insee_when_org_is_a_commune(self, mock_get):
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))

        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)

        # Signal connected on on_create runs the task synchronously (eager Celery).
        org.reload()
        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_assigns_zone_for_departement(self, mock_get):
        GeoZoneFactory(
            id="fr:departement:13", level="fr:departement", name="Bouches-du-Rhône", code="13"
        )
        mock_get.return_value = _mock_search_response(_departement_result(self.SIRET, "13"))

        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone == "fr:departement:13"
        assert org.extras.get("code_insee") == "13"

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_branch_siret_is_accepted_via_matching_etablissements(self, mock_get):
        """A non-headquarters SIRET still maps to the entity via matching_etablissements."""
        self._paris_zone()
        branch_siret = self.SIRET
        siege_siret = "21750055200099"  # different establishment
        mock_get.return_value = _mock_search_response(
            {
                "results": [
                    {
                        "siren": branch_siret[:9],
                        "nature_juridique": "7210",
                        "siege": {"siret": siege_siret, "code_commune": "75056"},
                        "matching_etablissements": [{"siret": branch_siret}],
                    }
                ]
            }
        )

        org = OrganizationFactory(business_number_id=branch_siret, zone=None)
        org.reload()
        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_does_not_assign_zone_for_non_collectivite(self, mock_get):
        mock_get.return_value = _mock_search_response(_non_collectivite_result(self.SIRET))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone is None
        assert org.extras.get("code_insee") is None

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_does_not_assign_unknown_geozone(self, mock_get):
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "99999"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone is None
        assert org.extras.get("code_insee") is None

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_task_is_idempotent(self, mock_get):
        """Running the task again on an org already linked to its zone is a no-op."""
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        previous_last_modified = org.last_modified

        lookup_organization_zone(str(org.id))
        org.reload()
        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"
        assert org.last_modified == previous_last_modified  # no extra save

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_clears_zone_when_siret_becomes_non_collectivite(self, mock_get):
        """Editing the SIRET to a private company clears the previously-set zone."""
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone == "fr:commune:75056"

        mock_get.return_value = _mock_search_response(_non_collectivite_result(self.OTHER_SIRET))
        org = Organization.objects.get(pk=org.pk)
        org.business_number_id = self.OTHER_SIRET
        org.save()
        org.reload()

        assert org.zone is None
        assert org.extras.get("code_insee") is None

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_clears_zone_when_siret_is_removed(self, mock_get):
        """Removing the SIRET clears the previously-set zone."""
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone == "fr:commune:75056"

        org = Organization.objects.get(pk=org.pk)
        org.business_number_id = None
        org.save()
        org.reload()

        assert org.zone is None
        assert org.extras.get("code_insee") is None

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_transient_failure_preserves_existing_zone(self, mock_get):
        """A 5xx or network error on a re-lookup must not destroy a correct enrichment."""
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone == "fr:commune:75056"

        # Next SIRET update triggers a fresh lookup that the API can't serve.
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        org = Organization.objects.get(pk=org.pk)
        org.business_number_id = self.OTHER_SIRET
        org.save()
        org.reload()

        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_siret_mismatch_in_response_is_ignored(self, mock_get):
        """/search is fuzzy; a top result not containing the queried SIRET is dropped."""
        self._paris_zone()
        # Top result has a different siege.siret AND no matching_etablissements entry.
        mock_get.return_value = _mock_search_response(
            {
                "results": [
                    {
                        "siren": "123456789",
                        "nature_juridique": "7210",
                        "siege": {"siret": "12345678900012", "code_commune": "75056"},
                        "matching_etablissements": [{"siret": "12345678900099"}],
                    }
                ]
            }
        )
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone is None
        assert org.extras.get("code_insee") is None

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_siret_mismatch_preserves_existing_zone(self, mock_get):
        """A subsequent unreliable response must not wipe a previously-derived zone."""
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone == "fr:commune:75056"

        # Edit SIRET; API returns an unrelated entity that doesn't include the queried SIRET.
        mock_get.return_value = _mock_search_response(
            {
                "results": [
                    {
                        "siren": "123456789",
                        "nature_juridique": "7210",
                        "siege": {"siret": "12345678900012", "code_commune": "13001"},
                        "matching_etablissements": [{"siret": "12345678900099"}],
                    }
                ]
            }
        )
        org = Organization.objects.get(pk=org.pk)
        org.business_number_id = self.OTHER_SIRET
        org.save()
        org.reload()

        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_invalid_json_response_preserves_existing_zone(self, mock_get):
        """A 200 response with a non-JSON body degrades to None and preserves data."""
        self._paris_zone()
        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = OrganizationFactory(business_number_id=self.SIRET, zone=None)
        org.reload()
        assert org.zone == "fr:commune:75056"

        broken = MagicMock()
        broken.raise_for_status = MagicMock()
        broken.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = broken
        org = Organization.objects.get(pk=org.pk)
        org.business_number_id = self.OTHER_SIRET
        org.save()
        org.reload()

        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"

    @patch("udata.core.organization.api_entreprise.requests.get")
    def test_signal_fires_when_siret_is_updated(self, mock_get):
        self._paris_zone()
        # First save without SIRET should not call the API.
        org = OrganizationFactory(business_number_id=None, zone=None)
        assert not mock_get.called

        mock_get.return_value = _mock_search_response(_commune_result(self.SIRET, "75056"))
        org = Organization.objects.get(pk=org.pk)
        org.business_number_id = self.SIRET
        org.save()
        org.reload()

        assert mock_get.called
        assert org.zone == "fr:commune:75056"
        assert org.extras.get("code_insee") == "75056"
