from enum import StrEnum, auto
from typing import assert_never

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

    PUBLIC_AUTHORITIES = "confidentiality_of_proceedings_of_public_authorities"
    INTERNATIONAL_RELATIONS = "international_relations_public_security_or_national_defence"
    COURSE_OF_JUSTICE = "course_of_justice_or_fair_trial"
    COMMERCIAL_CONFIDENTIALITY = "confidentiality_of_commercial_or_industrial_information"
    INTELLECTUAL_PROPERTY = "intellectual_property_rights"
    PERSONAL_DATA = "confidentiality_of_personal_data"
    VOLUNTARY_SUPPLIER = "protection_of_voluntary_information_suppliers"
    ENVIRONMENTAL_PROTECTION = "protection_of_environment"

    @property
    def label(self):
        """Returns the label for this limitation category."""
        match self:
            case InspireLimitationCategory.PUBLIC_AUTHORITIES:
                return _("Confidentiality of public authorities proceedings")
            case InspireLimitationCategory.INTERNATIONAL_RELATIONS:
                return _("International relations, public security or national defence")
            case InspireLimitationCategory.COURSE_OF_JUSTICE:
                return _("Course of justice")
            case InspireLimitationCategory.COMMERCIAL_CONFIDENTIALITY:
                return _("Commercial or industrial confidentiality")
            case InspireLimitationCategory.INTELLECTUAL_PROPERTY:
                return _("Intellectual property rights")
            case InspireLimitationCategory.PERSONAL_DATA:
                return _("Personal data confidentiality")
            case InspireLimitationCategory.VOLUNTARY_SUPPLIER:
                return _("Protection of voluntary information suppliers")
            case InspireLimitationCategory.ENVIRONMENTAL_PROTECTION:
                return _("Environmental protection")
            case _:
                assert_never(self)

    def localized_label(self, country: str):
        """
        Returns the technical label that should be used.
        At the INSPIRE level, the labels are the following: https://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess
        Make sure that localization match national labels standard. Example in France, where metadata follow the CNIG INSPIRE recommendation guide:
        https://cnig.gouv.fr/IMG/pdf/guide-de-saisie-des-elements-de-metadonnees-inspire-v2.0-1.pdf
        """
        match self:
            case InspireLimitationCategory.PUBLIC_AUTHORITIES:
                match country:
                    case "fr":
                        return "L124-4-I-1 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.a)"
                    case _:
                        return "public access limited according to Article 13(1)(a) of the INSPIRE Directive"
            case InspireLimitationCategory.INTERNATIONAL_RELATIONS:
                match country:
                    case "fr":
                        return "L124-5-II-1 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.b)"
                    case _:
                        return "public access limited according to Article 13(1)(b) of the INSPIRE Directive"
            case InspireLimitationCategory.COURSE_OF_JUSTICE:
                match country:
                    case "fr":
                        return "L124-5-II-2 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.c)"
                    case _:
                        return "public access limited according to Article 13(1)(c) of the INSPIRE Directive"
            case InspireLimitationCategory.COMMERCIAL_CONFIDENTIALITY:
                match country:
                    case "fr":
                        return "L124-4-I-1 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.d)"
                    case _:
                        return "public access limited according to Article 13(1)(d) of the INSPIRE Directive"
            case InspireLimitationCategory.INTELLECTUAL_PROPERTY:
                match country:
                    case "fr":
                        return "L124-5-II-3 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.e)"
                    case _:
                        return "public access limited according to Article 13(1)(e) of the INSPIRE Directive"
            case InspireLimitationCategory.PERSONAL_DATA:
                match country:
                    case "fr":
                        return "L124-4-I-1 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.f)"
                    case _:
                        return "public access limited according to Article 13(1)(f) of the INSPIRE Directive"
            case InspireLimitationCategory.VOLUNTARY_SUPPLIER:
                match country:
                    case "fr":
                        return "L124-4-I-3 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.g)"
                    case _:
                        return "public access limited according to Article 13(1)(g) of the INSPIRE Directive"
            case InspireLimitationCategory.ENVIRONMENTAL_PROTECTION:
                match country:
                    case "fr":
                        return "L124-4-I-2 du code de l’environnement (Directive 2007/2/CE (INSPIRE), Article 13.1.h)"
                    case _:
                        return "public access limited according to Article 13(1)(h) of the INSPIRE Directive"
            case _:
                assert_never(self)

    @property
    def definition(self):
        """Returns the definition for this limitation category."""
        match self:
            case InspireLimitationCategory.PUBLIC_AUTHORITIES:
                return _(
                    "Public access to datasets and services would adversely affect the confidentiality of the proceedings of public authorities, where such confidentiality is provided for by law."
                )
            case InspireLimitationCategory.INTERNATIONAL_RELATIONS:
                return _(
                    "Public access to datasets and services would adversely affect international relations, public security or national defence."
                )
            case InspireLimitationCategory.COURSE_OF_JUSTICE:
                return _(
                    "Public access to datasets and services would adversely affect the course of justice, the ability of any person to receive a fair trial or the ability of a public authority to conduct an enquiry of a criminal or disciplinary nature."
                )
            case InspireLimitationCategory.COMMERCIAL_CONFIDENTIALITY:
                return _(
                    "Public access to datasets and services would adversely affect the confidentiality of commercial or industrial information, where such confidentiality is provided for by national or Community law to protect a legitimate economic interest, including the public interest in maintaining statistical confidentiality and tax secrecy."
                )
            case InspireLimitationCategory.INTELLECTUAL_PROPERTY:
                return _(
                    "Public access to datasets and services would adversely affect intellectual property rights."
                )
            case InspireLimitationCategory.PERSONAL_DATA:
                return _(
                    "Public access to datasets and services would adversely affect the confidentiality of personal data and/or files relating to a natural person where that person has not consented to the disclosure of the information to the public, where such confidentiality is provided for by national or Community law."
                )
            case InspireLimitationCategory.VOLUNTARY_SUPPLIER:
                return _(
                    "Public access to datasets and services would adversely affect the interests or protection of any person who supplied the information requested on a voluntary basis without being under, or capable of being put under, a legal obligation to do so, unless that person has consented to the release of the information concerned."
                )
            case InspireLimitationCategory.ENVIRONMENTAL_PROTECTION:
                return _(
                    "Public access to datasets and services would adversely affect the protection of the environment to which such information relates, such as the location of rare species."
                )
            case _:
                assert_never(self)

    @property
    def url(self):
        """Returns the INSPIRE url for this limitation category."""
        match self:
            case InspireLimitationCategory.PUBLIC_AUTHORITIES:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1a"
            case InspireLimitationCategory.INTERNATIONAL_RELATIONS:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1b"
            case InspireLimitationCategory.COURSE_OF_JUSTICE:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1c"
            case InspireLimitationCategory.COMMERCIAL_CONFIDENTIALITY:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1d"
            case InspireLimitationCategory.INTELLECTUAL_PROPERTY:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1e"
            case InspireLimitationCategory.PERSONAL_DATA:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1f"
            case InspireLimitationCategory.VOLUNTARY_SUPPLIER:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1g"
            case InspireLimitationCategory.ENVIRONMENTAL_PROTECTION:
                return "http://inspire.ec.europa.eu/metadata-codelist/LimitationsOnPublicAccess/INSPIRE_Directive_Article13_1h"
            case _:
                assert_never(self)

    @classmethod
    def get_labels(cls):
        """Returns a dictionary of all INSPIRE limitation category labels."""
        return {member: member.label for member in cls}

    @classmethod
    def get_category_from_localized_label(cls, label: str, country: str):
        for member in cls:
            if slugify(member.localized_label(country)) == slugify(label):
                return member
