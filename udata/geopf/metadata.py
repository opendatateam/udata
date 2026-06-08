from xml.sax.saxutils import escape

# France metropolitan bounding box (fallback when dataset has no spatial coverage)
FRANCE_METRO_BBOX = (-5.14, 41.33, 9.56, 51.09)  # west, south, east, north

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
      <gmd:language>
        <gmd:LanguageCode
          codeList="http://www.loc.gov/standards/iso639-2/"
          codeListValue="fre">fre</gmd:LanguageCode>
      </gmd:language>
      {keywords_block}
      {constraints_block}
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
      </gmd:extent>
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

CONSTRAINTS_TEMPLATE = """\
      <gmd:resourceConstraints>
        <gmd:MD_LegalConstraints>
          <gmd:otherConstraints>
            <gco:CharacterString>{license_text}</gco:CharacterString>
          </gmd:otherConstraints>
        </gmd:MD_LegalConstraints>
      </gmd:resourceConstraints>"""


def _bbox(dataset):
    """Return (west, south, east, north) from dataset.spatial or France metro default."""
    if dataset.spatial and dataset.spatial.geom:
        geom = dataset.spatial.geom
        # MultiPolygon: list of polygons, each a list of rings, each a list of [lon, lat]
        coords = [coord for polygon in geom["coordinates"] for ring in polygon for coord in ring]
        if coords:
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return min(lons), min(lats), max(lons), max(lats)
    return FRANCE_METRO_BBOX


def _org_name(dataset):
    if dataset.organization:
        return dataset.organization.name
    if dataset.owner:
        return dataset.owner.fullname
    return ""


def _license_text(dataset):
    if not dataset.license:
        return ""
    # Follow license_to_rdf() pattern from udata/core/dataset/rdf.py
    if dataset.license.url:
        return dataset.license.url
    return dataset.license.title or ""


def dataset_to_iso19115(dataset) -> bytes:
    file_identifier = str(dataset.id)
    abstract = dataset.description or dataset.title

    keywords_block = ""
    if dataset.tags:
        kw_elems = "\n          ".join(
            f"<gmd:keyword><gco:CharacterString>{escape(t)}</gco:CharacterString></gmd:keyword>"
            for t in dataset.tags
        )
        keywords_block = KEYWORDS_TEMPLATE.format(keyword_elements=kw_elems)

    constraints_block = ""
    license_text = _license_text(dataset)
    if license_text:
        constraints_block = CONSTRAINTS_TEMPLATE.format(license_text=escape(license_text))

    west, south, east, north = _bbox(dataset)

    xml = TEMPLATE.format(
        file_identifier=escape(file_identifier),
        org_name=escape(_org_name(dataset)),
        date_stamp=dataset.last_modified.strftime("%Y-%m-%d"),
        title=escape(dataset.title),
        created_at=dataset.created_at.strftime("%Y-%m-%d"),
        abstract=escape(abstract),
        keywords_block=keywords_block,
        constraints_block=constraints_block,
        west=west,
        east=east,
        south=south,
        north=north,
    )
    return xml.encode("utf-8")
