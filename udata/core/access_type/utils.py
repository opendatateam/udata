from udata.core.access_type.constants import (
    INSPIRE_13_A_PUBLIC_AUTHORITIES,
    INSPIRE_13_B_INTERNATIONAL_RELATIONS,
    INSPIRE_13_C_COURSE_OF_JUSTICE,
    INSPIRE_13_D_COMMERCIAL_CONFIDENTIALITY,
    INSPIRE_13_E_INTELLECTUAL_PROPERTY,
    INSPIRE_13_F_PERSONAL_DATA,
    INSPIRE_13_G_VOLUNTARY_SUPPLIER,
    INSPIRE_13_H_ENVIRONMENTAL_PROTECTION,
)
from udata.i18n import lazy_gettext as _


def get_inspire_limitation_labels():
    """
    Returns a dictionary of INSPIRE limitation category labels.
    """
    return {
        INSPIRE_13_A_PUBLIC_AUTHORITIES: _("Confidentiality of public authorities proceedings"),
        INSPIRE_13_B_INTERNATIONAL_RELATIONS: _("International relations, public security or national defence"),
        INSPIRE_13_C_COURSE_OF_JUSTICE: _("Course of justice"),
        INSPIRE_13_D_COMMERCIAL_CONFIDENTIALITY: _("Commercial or industrial confidentiality"),
        INSPIRE_13_E_INTELLECTUAL_PROPERTY: _("Intellectual property rights"),
        INSPIRE_13_F_PERSONAL_DATA: _("Personal data confidentiality"),
        INSPIRE_13_G_VOLUNTARY_SUPPLIER: _("Protection of voluntary information suppliers"),
        INSPIRE_13_H_ENVIRONMENTAL_PROTECTION: _("Environmental protection"),
    }


def get_inspire_limitation_definition(category):
    """
    Returns the definition for an INSPIRE limitation category.
    Based on the INSPIRE Directive metadata codelist for LimitationsOnPublicAccess.
    """
    definitions = {
        INSPIRE_13_A_PUBLIC_AUTHORITIES: _(
            "The confidentiality of the proceedings of public authorities, where such confidentiality is provided for by law."
        ),
        INSPIRE_13_B_INTERNATIONAL_RELATIONS: _(
            "International relations, public security or national defence."
        ),
        INSPIRE_13_C_COURSE_OF_JUSTICE: _(
            "The course of justice, the ability of any person to receive a fair trial or the ability of a public authority to conduct an enquiry of a criminal or disciplinary nature."
        ),
        INSPIRE_13_D_COMMERCIAL_CONFIDENTIALITY: _(
            "The confidentiality of commercial or industrial information, where such confidentiality is provided for by national or Community law to protect a legitimate economic interest."
        ),
        INSPIRE_13_E_INTELLECTUAL_PROPERTY: _(
            "Intellectual property rights."
        ),
        INSPIRE_13_F_PERSONAL_DATA: _(
            "The confidentiality of personal data and/or files relating to a natural person where that person has not consented to the disclosure."
        ),
        INSPIRE_13_G_VOLUNTARY_SUPPLIER: _(
            "The interests or protection of any person who supplied the information requested on a voluntary basis without being under a legal obligation."
        ),
        INSPIRE_13_H_ENVIRONMENTAL_PROTECTION: _(
            "The protection of the environment to which such information relates, such as the location of rare species."
        ),
    }
    return definitions.get(category, _("Unknown limitation category"))
