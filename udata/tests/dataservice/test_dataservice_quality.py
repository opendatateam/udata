from udata.core.access_type.constants import AccessType
from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import LicenseFactory
from udata.tests.api import PytestOnlyAPITestCase


class DataserviceComputeQualityTest(PytestOnlyAPITestCase):
    def test_empty_dataservice_fails_every_criterion_except_open_access(self):
        ds = DataserviceFactory.build(
            description="",
            base_api_url=None,
            machine_documentation_url=None,
            technical_documentation_url=None,
            business_documentation_url=None,
            license=None,
            availability=None,
            availability_url=None,
            rate_limiting=None,
            rate_limiting_url=None,
            contact_points=[],
            access_type=AccessType.OPEN,
        )
        quality = ds.compute_quality()

        assert quality["has_description"] is False
        assert quality["has_machine_documentation"] is False
        assert quality["has_technical_documentation"] is False
        assert quality["license"] is False
        assert quality["has_contact_point"] is False
        assert quality["has_base_api_url"] is False
        assert quality["availability_documented"] is False
        assert quality["rate_limiting_documented"] is False
        assert quality["has_business_documentation"] is False
        assert quality["access_conditions_clear"] is True

    def test_full_dataservice_passes_every_criterion(self):
        contact = ContactPointFactory()
        ds = DataserviceFactory.build(
            description="x" * 200,
            base_api_url="https://api.example.com",
            machine_documentation_url="https://api.example.com/openapi.json",
            technical_documentation_url="https://api.example.com/docs",
            business_documentation_url="https://example.com/about",
            license=LicenseFactory(),
            availability=99.9,
            rate_limiting="100 req/min",
            contact_points=[contact],
            access_type=AccessType.RESTRICTED,
            authorization_request_url="https://example.com/request-access",
        )
        quality = ds.compute_quality()

        assert all(
            quality[key] is True
            for key in [
                "has_description",
                "has_machine_documentation",
                "has_technical_documentation",
                "has_business_documentation",
                "license",
                "has_contact_point",
                "has_base_api_url",
                "availability_documented",
                "rate_limiting_documented",
                "access_conditions_clear",
            ]
        )

    def test_restricted_access_without_authorization_url_fails(self):
        ds = DataserviceFactory.build(
            access_type=AccessType.RESTRICTED, authorization_request_url=None
        )
        assert ds.compute_quality()["access_conditions_clear"] is False

    def test_zero_availability_counts_as_documented(self):
        ds = DataserviceFactory.build(availability=0.0, availability_url=None)
        assert ds.compute_quality()["availability_documented"] is True

    def test_open_with_account_requires_authorization_url(self):
        ds = DataserviceFactory.build(
            access_type=AccessType.OPEN_WITH_ACCOUNT, authorization_request_url=None
        )
        assert ds.compute_quality()["access_conditions_clear"] is False


class DataserviceQualityScoreTest(PytestOnlyAPITestCase):
    def test_score_is_count_of_true_criteria_over_ten(self):
        ds = DataserviceFactory.build()
        quality = {
            "has_description": True,
            "has_machine_documentation": True,
            "has_technical_documentation": False,
            "license": True,
            "has_contact_point": False,
            "has_base_api_url": True,
            "availability_documented": False,
            "rate_limiting_documented": False,
            "has_business_documentation": False,
            "access_conditions_clear": True,
        }
        assert ds.compute_quality_score(quality) == 0.5

    def test_all_false_scores_zero(self):
        ds = DataserviceFactory.build()
        quality = {
            k: False
            for k in [
                "has_description",
                "has_machine_documentation",
                "has_technical_documentation",
                "license",
                "has_contact_point",
                "has_base_api_url",
                "availability_documented",
                "rate_limiting_documented",
                "has_business_documentation",
                "access_conditions_clear",
            ]
        }
        assert ds.compute_quality_score(quality) == 0.0

    def test_all_true_scores_one(self):
        ds = DataserviceFactory.build()
        quality = {
            k: True
            for k in [
                "has_description",
                "has_machine_documentation",
                "has_technical_documentation",
                "license",
                "has_contact_point",
                "has_base_api_url",
                "availability_documented",
                "rate_limiting_documented",
                "has_business_documentation",
                "access_conditions_clear",
            ]
        }
        assert ds.compute_quality_score(quality) == 1.0
