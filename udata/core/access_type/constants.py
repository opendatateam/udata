from enum import StrEnum

from udata.i18n import lazy_gettext as _


class AccessType(StrEnum):
    OPEN = "open"
    OPEN_WITH_ACCOUNT = "open_with_account"
    RESTRICTED = "restricted"


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
        labels = {
            self.PUBLIC_AUTHORITIES: _("Confidentiality of public authorities proceedings"),
            self.INTERNATIONAL_RELATIONS: _(
                "International relations, public security or national defence"
            ),
            self.COURSE_OF_JUSTICE: _("Course of justice"),
            self.COMMERCIAL_CONFIDENTIALITY: _("Commercial or industrial confidentiality"),
            self.INTELLECTUAL_PROPERTY: _("Intellectual property rights"),
            self.PERSONAL_DATA: _("Personal data confidentiality"),
            self.VOLUNTARY_SUPPLIER: _("Protection of voluntary information suppliers"),
            self.ENVIRONMENTAL_PROTECTION: _("Environmental protection"),
        }
        return labels.get(self, _("Unknown limitation category"))

    @property
    def definition(self):
        """Returns the definition for this limitation category."""
        definitions = {
            self.PUBLIC_AUTHORITIES: _(
                "The confidentiality of the proceedings of public authorities, where such confidentiality is provided for by law."
            ),
            self.INTERNATIONAL_RELATIONS: _(
                "International relations, public security or national defence."
            ),
            self.COURSE_OF_JUSTICE: _(
                "The course of justice, the ability of any person to receive a fair trial or the ability of a public authority to conduct an enquiry of a criminal or disciplinary nature."
            ),
            self.COMMERCIAL_CONFIDENTIALITY: _(
                "The confidentiality of commercial or industrial information, where such confidentiality is provided for by national or Community law to protect a legitimate economic interest."
            ),
            self.INTELLECTUAL_PROPERTY: _("Intellectual property rights."),
            self.PERSONAL_DATA: _(
                "The confidentiality of personal data and/or files relating to a natural person where that person has not consented to the disclosure."
            ),
            self.VOLUNTARY_SUPPLIER: _(
                "The interests or protection of any person who supplied the information requested on a voluntary basis without being under a legal obligation."
            ),
            self.ENVIRONMENTAL_PROTECTION: _(
                "The protection of the environment to which such information relates, such as the location of rare species."
            ),
        }
        return definitions.get(self, _("Unknown limitation category"))

    @classmethod
    def get_labels(cls):
        """Returns a dictionary of all INSPIRE limitation category labels."""
        return {member: member.label for member in cls}
