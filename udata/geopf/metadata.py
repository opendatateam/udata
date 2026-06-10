from xml.sax.saxutils import escape

# ISO 19115 MD_TopicCategoryCode → matching French/English tag keywords
TOPIC_MAP = {
    "farming": ["agriculture", "agricole", "farming"],
    "biota": ["biodiversite", "faune", "flore", "biodiversity", "nature"],
    "boundaries": ["limites", "boundaries"],
    "climatologyMeteorologyAtmosphere": ["meteo", "climat", "climate", "atmosphere"],
    "economy": ["economie", "economy", "commerce", "finance"],
    "elevation": ["altitude", "elevation", "mnt", "dem", "relief"],
    "environment": ["environnement", "environment", "ecologie"],
    "geoscientificInformation": ["geologie", "geology", "sol", "soil"],
    "health": ["sante", "health"],
    "imageryBaseMapsEarthCover": ["orthophoto", "satellite", "imagery", "occupation-du-sol"],
    "inlandWaters": ["eau", "water", "riviere", "hydrologie", "hydrology", "lac"],
    "location": ["adresse", "address", "localisation", "location"],
    "oceans": ["mer", "ocean", "maritime", "cotier"],
    "planningCadastre": ["cadastre", "urbanisme", "planning"],
    "society": ["population", "demographie", "societe"],
    "structure": ["batiment", "building", "infrastructure"],
    "transportation": ["transport", "route", "road", "voirie", "rail", "mobilite"],
    "utilitiesCommunication": ["reseau", "telecom", "energie"],
}

TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<gmd:MD_Metadata
  xmlns:gmd="http://www.isotc211.org/2005/gmd"
  xmlns:gco="http://www.isotc211.org/2005/gco"
  xmlns:gml="http://www.opengis.net/gml">
  <gmd:fileIdentifier>
    <gco:CharacterString>{file_identifier}</gco:CharacterString>
  </gmd:fileIdentifier>
  <gmd:language>
    <gmd:LanguageCode
      codeList="http://www.loc.gov/standards/iso639-2/"
      codeListValue="fre">fre</gmd:LanguageCode>
  </gmd:language>
  <gmd:hierarchyLevel>
    <gmd:MD_ScopeCode
      codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_ScopeCode"
      codeListValue="dataset">dataset</gmd:MD_ScopeCode>
  </gmd:hierarchyLevel>
  <gmd:contact>
    <gmd:CI_ResponsibleParty>
      <gmd:organisationName>
        <gco:CharacterString>{org_name}</gco:CharacterString>
      </gmd:organisationName>
      {contact_info_block}
      <gmd:role>
        <gmd:CI_RoleCode
          codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_RoleCode"
          codeListValue="pointOfContact">pointOfContact</gmd:CI_RoleCode>
      </gmd:role>
    </gmd:CI_ResponsibleParty>
  </gmd:contact>
  <gmd:dateStamp>
    <gco:Date>{date_stamp}</gco:Date>
  </gmd:dateStamp>
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:title>
            <gco:CharacterString>{title}</gco:CharacterString>
          </gmd:title>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date>
                <gco:Date>{created_at}</gco:Date>
              </gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode
                  codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode"
                  codeListValue="creation">creation</gmd:CI_DateTypeCode>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
      <gmd:abstract>
        <gco:CharacterString>{abstract}</gco:CharacterString>
      </gmd:abstract>
      {point_of_contact_block}
      <gmd:language>
        <gmd:LanguageCode
          codeList="http://www.loc.gov/standards/iso639-2/"
          codeListValue="fre">fre</gmd:LanguageCode>
      </gmd:language>
      {keywords_block}
      {topic_category_block}
      {extent_block}
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""

KEYWORDS_TEMPLATE = """\
      <gmd:descriptiveKeywords>
        <gmd:MD_Keywords>
          {keyword_elements}
        </gmd:MD_Keywords>
      </gmd:descriptiveKeywords>"""

CONTACT_INFO_TEMPLATE = """\
      <gmd:contactInfo>
        <gmd:CI_Contact>
          <gmd:address>
            <gmd:CI_Address>
              <gmd:electronicMailAddress>
                <gco:CharacterString>{email}</gco:CharacterString>
              </gmd:electronicMailAddress>
            </gmd:CI_Address>
          </gmd:address>
        </gmd:CI_Contact>
      </gmd:contactInfo>"""

POINT_OF_CONTACT_TEMPLATE = """\
      <gmd:pointOfContact>
        <gmd:CI_ResponsibleParty>
          <gmd:organisationName>
            <gco:CharacterString>{org_name}</gco:CharacterString>
          </gmd:organisationName>
          {contact_info_block}
          <gmd:role>
            <gmd:CI_RoleCode
              codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_RoleCode"
              codeListValue="pointOfContact">pointOfContact</gmd:CI_RoleCode>
          </gmd:role>
        </gmd:CI_ResponsibleParty>
      </gmd:pointOfContact>"""

TOPIC_CATEGORY_TEMPLATE = """\
      <gmd:topicCategory>
        <gmd:MD_TopicCategoryCode>{topic}</gmd:MD_TopicCategoryCode>
      </gmd:topicCategory>"""

EXTENT_TEMPLATE = """\
      <gmd:extent>
        <gmd:EX_Extent>
          <gmd:geographicElement>
            <gmd:EX_GeographicBoundingBox>
              <gmd:westBoundLongitude><gco:Decimal>{west}</gco:Decimal></gmd:westBoundLongitude>
              <gmd:eastBoundLongitude><gco:Decimal>{east}</gco:Decimal></gmd:eastBoundLongitude>
              <gmd:southBoundLatitude><gco:Decimal>{south}</gco:Decimal></gmd:southBoundLatitude>
              <gmd:northBoundLatitude><gco:Decimal>{north}</gco:Decimal></gmd:northBoundLatitude>
            </gmd:EX_GeographicBoundingBox>
          </gmd:geographicElement>
        </gmd:EX_Extent>
      </gmd:extent>"""


def _bbox(dataset):
    """Return (west, south, east, north) from dataset.spatial.geom, or None if unavailable.

    Zone-based coverage has no stored geometry and is not supported.
    """
    if dataset.spatial and dataset.spatial.geom:
        geom = dataset.spatial.geom
        coords = [coord for polygon in geom["coordinates"] for ring in polygon for coord in ring]
        if coords:
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return min(lons), min(lats), max(lons), max(lats)
    return None


def _org_name(dataset):
    if dataset.organization:
        return dataset.organization.name
    if dataset.owner:
        return dataset.owner.fullname
    return ""


def _contact_email(dataset):
    for cp in dataset.contact_points or []:
        if cp.email:
            return cp.email
    return None


def _topic_category(dataset):
    if dataset.tags:
        tags_lower = {t.lower() for t in dataset.tags}
        return next(
            (code for code, keywords in TOPIC_MAP.items() if tags_lower & set(keywords)), None
        )
    return None


def dataset_to_iso19115(dataset) -> bytes:
    file_identifier = str(dataset.id)
    abstract = dataset.description or dataset.title
    org_name = _org_name(dataset)
    email = _contact_email(dataset)

    contact_info_block = CONTACT_INFO_TEMPLATE.format(email=escape(email)) if email else ""

    point_of_contact_block = (
        POINT_OF_CONTACT_TEMPLATE.format(
            org_name=escape(org_name),
            contact_info_block=contact_info_block,
        )
        if org_name
        else ""
    )

    keywords_block = ""
    if dataset.tags:
        kw_elems = "\n          ".join(
            f"<gmd:keyword><gco:CharacterString>{escape(t)}</gco:CharacterString></gmd:keyword>"
            for t in dataset.tags
        )
        keywords_block = KEYWORDS_TEMPLATE.format(keyword_elements=kw_elems)

    topic = _topic_category(dataset)
    topic_category_block = TOPIC_CATEGORY_TEMPLATE.format(topic=topic) if topic else ""

    bbox = _bbox(dataset)
    extent_block = (
        EXTENT_TEMPLATE.format(west=bbox[0], south=bbox[1], east=bbox[2], north=bbox[3])
        if bbox
        else ""
    )

    xml = TEMPLATE.format(
        file_identifier=escape(file_identifier),
        org_name=escape(org_name),
        contact_info_block=contact_info_block,
        date_stamp=dataset.last_modified.strftime("%Y-%m-%d"),
        title=escape(dataset.title),
        created_at=dataset.created_at.strftime("%Y-%m-%d"),
        abstract=escape(abstract),
        point_of_contact_block=point_of_contact_block,
        keywords_block=keywords_block,
        topic_category_block=topic_category_block,
        extent_block=extent_block,
    )
    return xml.encode("utf-8")
