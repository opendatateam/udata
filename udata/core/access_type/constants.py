from enum import StrEnum, auto
from typing import assert_never

from flask_babel import LazyString
from slugify import slugify

from udata.i18n import lazy_gettext as _


class AccessType(StrEnum):
    OPEN = auto()
    OPEN_WITH_ACCOUNT = auto()
    RESTRICTED = auto()

    @property
    def url(self):
        """Returns the european url for this access type."""
        match self:
            case AccessType.OPEN | AccessType.OPEN_WITH_ACCOUNT:
                return "http://publications.europa.eu/resource/authority/access-right/PUBLIC"
            case AccessType.RESTRICTED:
                # Actually map to NON_PUBLIC and not restricted following the definition in the EU vocabulary:
                # https://op.europa.eu/en/web/eu-vocabularies/concept-scheme/-/resource?uri=http://publications.europa.eu/resource/authority/access-right.
                return "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC"
            case _:
                assert_never(self)


class AccessAudienceType(StrEnum):
    ADMINISTRATION = "local_authority_and_administration"
    COMPANY = "company_and_association"
    PRIVATE = "private"


class AccessAudienceCondition(StrEnum):
    YES = "yes"
    NO = "no"
    UNDER_CONDITIONS = "under_condition"


class InspireLimitationCategory(StrEnum):
    """INSPIRE Directive Article 13(1) limitation reason categories"""

    PUBLIC_AUTHORITIES = (
        "confidentiality_of_proceedings_of_public_authorities",
        _("Confidentiality of public authorities proceedings"),
        {
            "fr": "L124-4-I-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.a)",
            "en": "public access limited according to Article 13(1)(a) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect the confidentiality of the proceedings of public authorities, where such confidentiality is provided for by law."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1a",
    )
    INTERNATIONAL_RELATIONS = (
        "international_relations_public_security_or_national_defence",
        _("International relations, public security or national defence"),
        {
            "fr": "L124-5-II-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.b)",
            "en": "public access limited according to Article 13(1)(b) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect international relations, public security or national defence."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1b",
    )
    COURSE_OF_JUSTICE = (
        "course_of_justice_or_fair_trial",
        _("Course of justice"),
        {
            "fr": "L124-5-II-2 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.c)",
            "en": "public access limited according to Article 13(1)(c) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect the course of justice, the ability of any person to receive a fair trial or the ability of a public authority to conduct an enquiry of a criminal or disciplinary nature."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1c",
    )
    COMMERCIAL_CONFIDENTIALITY = (
        "confidentiality_of_commercial_or_industrial_information",
        _("Commercial or industrial confidentiality"),
        {
            "fr": "L124-4-I-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.d)",
            "en": "public access limited according to Article 13(1)(d) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect the confidentiality of commercial or industrial information, where such confidentiality is provided for by national or Community law to protect a legitimate economic interest, including the public interest in maintaining statistical confidentiality and tax secrecy."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1d",
    )
    INTELLECTUAL_PROPERTY = (
        "intellectual_property_rights",
        _("Intellectual property rights"),
        {
            "fr": "L124-5-II-3 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.e)",
            "en": "public access limited according to Article 13(1)(e) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect intellectual property rights."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1e",
    )
    PERSONAL_DATA = (
        "confidentiality_of_personal_data",
        _("Personal data confidentiality"),
        {
            "fr": "L124-4-I-1 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.f)",
            "en": "public access limited according to Article 13(1)(f) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect the confidentiality of personal data and/or files relating to a natural person where that person has not consented to the disclosure of the information to the public, where such confidentiality is provided for by national or Community law."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1f",
    )
    VOLUNTARY_SUPPLIER = (
        "protection_of_voluntary_information_suppliers",
        _("Protection of voluntary information suppliers"),
        {
            "fr": "L124-4-I-3 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.g)",
            "en": "public access limited according to Article 13(1)(g) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect the interests or protection of any person who supplied the information requested on a voluntary basis without being under, or capable of being put under, a legal obligation to do so, unless that person has consented to the release of the information concerned."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1g",
    )
    ENVIRONMENTAL_PROTECTION = (
        "protection_of_environment",
        _("Environmental protection"),
        {
            "fr": "L124-4-I-2 du code de l'environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.h)",
            "en": "public access limited according to Article 13(1)(h) of the INSPIRE Directive",
        },
        _(
            "Public access to datasets and services would adversely affect the protection of the environment to which such information relates, such as the location of rare species."
        ),
        "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1h",
    )

    def __new__(
        cls,
        id: str,
        label: LazyString,
        localized_labels: dict[str, str],
        definition: LazyString,
        url: str,
    ):
        # Set _value_ so the enum value-based lookup depends only on the id field.
        # See https://docs.python.org/3/howto/enum.html#when-to-use-new-vs-init
        obj = str.__new__(cls, id)
        obj._value_ = id
        obj._label = label  # type: ignore[misc]
        obj._localized_labels = localized_labels  # type: ignore[misc]
        obj._definition = definition  # type: ignore[misc]
        obj._url = url  # type: ignore[misc]
        return obj

    @property
    def id(self) -> str:
        return self.value

    @property
    def label(self) -> LazyString:
        return self._label  # type: ignore[misc]

    @property
    def definition(self) -> LazyString:
        return self._definition  # type: ignore[misc]

    @property
    def url(self) -> str:
        return self._url  # type: ignore[misc]

    def localized_label(self, country: str) -> str:
        """
        Returns the technical label that should be used.
        At the INSPIRE level, the labels are the following: https://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess
        Make sure that localization match national labels standard. Example in France, where metadata follow the CNIG INSPIRE recommendation guide:
        https://cnig.gouv.fr/IMG/pdf/guide-de-saisie-des-elements-de-metadonnees-inspire-v2.0-1.pdf
        """
        return self._localized_labels.get(country, self._localized_labels.get("en"))  # type: ignore[misc]

    @classmethod
    def get_labels(cls):
        """Returns a dictionary of all INSPIRE limitation category labels."""
        return {member: member.label for member in cls}

    @classmethod
    def get_category_from_localized_label(cls, label: str, country: str):
        for member in cls:
            if slugify(member.localized_label(country)) == slugify(label):
                return member
