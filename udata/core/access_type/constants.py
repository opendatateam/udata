from enum import StrEnum, auto
from typing import assert_never

from udata.i18n import lazy_gettext as _


class AccessType(StrEnum):
    OPEN = auto()
    OPEN_WITH_ACCOUNT = auto()
    RESTRICTED = auto()


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

    @property
    def definition(self):
        """Returns the definition for this limitation category."""
        match self:
            case InspireLimitationCategory.PUBLIC_AUTHORITIES:
                return _(
                    "The confidentiality of the proceedings of public authorities, where such confidentiality is provided for by law."
                )
            case InspireLimitationCategory.INTERNATIONAL_RELATIONS:
                return _("International relations, public security or national defence.")
            case InspireLimitationCategory.COURSE_OF_JUSTICE:
                return _(
                    "The course of justice, the ability of any person to receive a fair trial or the ability of a public authority to conduct an enquiry of a criminal or disciplinary nature."
                )
            case InspireLimitationCategory.COMMERCIAL_CONFIDENTIALITY:
                return _(
                    "The confidentiality of commercial or industrial information, where such confidentiality is provided for by national or Community law to protect a legitimate economic interest."
                )
            case InspireLimitationCategory.INTELLECTUAL_PROPERTY:
                return _("Intellectual property rights.")
            case InspireLimitationCategory.PERSONAL_DATA:
                return _(
                    "The confidentiality of personal data and/or files relating to a natural person where that person has not consented to the disclosure."
                )
            case InspireLimitationCategory.VOLUNTARY_SUPPLIER:
                return _(
                    "The interests or protection of any person who supplied the information requested on a voluntary basis without being under a legal obligation."
                )
            case InspireLimitationCategory.ENVIRONMENTAL_PROTECTION:
                return _(
                    "The protection of the environment to which such information relates, such as the location of rare species."
                )
            case _:
                assert_never(self)

    @classmethod
    def get_labels(cls):
        """Returns a dictionary of all INSPIRE limitation category labels."""
        return {member: member.label for member in cls}
