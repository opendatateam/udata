from udata.core.access_type.constants import InspireLimitationCategory


class InspireLimitationCategoryTest:
    def test_get(self):
        assert (
            InspireLimitationCategory.lookup(
                "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1b"
            )
            is InspireLimitationCategory.INTERNATIONAL_RELATIONS
        )
        assert (
            InspireLimitationCategory.lookup(
                "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1b",
                "fr",
            )
            is InspireLimitationCategory.INTERNATIONAL_RELATIONS
        )
        assert (
            InspireLimitationCategory.lookup(
                "L124-5-II-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.b)",
                "fr",
            )
            is InspireLimitationCategory.INTERNATIONAL_RELATIONS
        )
        assert (
            InspireLimitationCategory.lookup(
                "public access limited according to Article 13(1)(b) of the INSPIRE Directive", "en"
            )
            is InspireLimitationCategory.INTERNATIONAL_RELATIONS
        )
        assert (
            InspireLimitationCategory.lookup(
                "l124-5-ii-1 du code de l'environnement (directive 2007/2/ce (inspire), article 13.1.b)",
                "fr",
            )
            is InspireLimitationCategory.INTERNATIONAL_RELATIONS
        )
        assert (
            InspireLimitationCategory.lookup(
                "L124-5-II-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.b)"
            )
            is None
        )
        assert (
            InspireLimitationCategory.lookup(
                "L124-5-II-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.b)",
                "en",
            )
            is None
        )
