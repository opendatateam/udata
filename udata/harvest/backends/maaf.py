import logging
import os
import re
from collections import OrderedDict
from urllib.parse import urljoin

from lxml import etree, html
from voluptuous import All, Any, In, Length, Lower, Optional, Schema

from udata.harvest.backends import BaseBackend
from udata.harvest.filters import (
    boolean,
    email,
    force_list,
    is_url,
    normalize_string,
    taglist,
    to_date,
)
from udata.harvest.models import HarvestItem
from udata.models import Checksum, License, Resource, SpatialCoverage, db
from udata.utils import get_by

log = logging.getLogger(__name__)

GRANULARITIES = {
    "commune": "fr/town",
    "france": "country",
    "pays": "country",
}

RE_NAME = re.compile(r"(\{(?P<url>.+)\})?(?P<name>.+)$")

ZONES = {
    "country/fr": "country/fr",
    "country/monde": "country-group/world",
}


FREQUENCIES = {
    "ponctuelle": "punctual",
    "temps réel": "continuous",
    "quotidienne": "daily",
    "hebdomadaire": "weekly",
    "bimensuelle": "semimonthly",
    "mensuelle": "monthly",
    "bimestrielle": "bimonthly",
    "trimestrielle": "quarterly",
    "semestrielle": "semiannual",
    "annuelle": "annual",
    "triennale": "triennial",
    "quinquennale": "quinquennial",
    "aucune": "unknown",
}

XSD_PATH = os.path.join(os.path.dirname(__file__), "maaf.xsd")

SSL_COMMENT = """
Le site exposant les données est protégé par un certificat délivré par
l'IGC/A (IGC officielle de l'État).
Une exception de sécurité peut apparaître si votre navigateur ne reconnait
pas cette autorité :
vous trouverez  la procédure à suivre pour éviter une telle alerte
à l'adresse :
http://www.ssi.gouv.fr/fr/anssi/services-securises/igc-a/\
modalites-de-verification-du-certificat-de-l-igc-a-rsa-4096.html
"""

schema = Schema(
    {
        Optional("digest"): All(str, Length(min=1)),
        "metadata": {
            "author": str,
            "author_email": Any(All(str, email), None),
            "extras": [{"key": str, "value": str}],
            "frequency": All(Lower, In(FREQUENCIES.keys())),
            "groups": Any(None, All(Lower, "agriculture et alimentation")),
            "id": str,
            "license_id": Any("fr-lo"),
            "maintainer": Any(str, None),
            "maintainer_email": Any(All(str, email), None),
            "notes": All(str, normalize_string),
            "organization": str,
            "private": boolean,
            "resources": All(
                force_list,
                [
                    {
                        "name": str,
                        "description": All(str, normalize_string),
                        "format": All(str, Lower, Any("cle", "csv", "pdf", "txt")),
                        Optional("last_modified"): All(str, to_date),
                        "url": All(str, is_url(full=True)),
                    }
                ],
            ),
            "state": Any(str, None),
            "supplier": str,
            "tags": All(str, taglist),
            "temporal_coverage_from": None,
            "temporal_coverage_to": None,
            "territorial_coverage": {
                "territorial_coverage_code": All(str, Lower, In(ZONES.keys())),
                "territorial_coverage_granularity": All(str, Lower, In(GRANULARITIES.keys())),
            },
            "title": str,
        },
    },
    required=True,
    extra=True,
)


LIST_KEYS = "extras", "resources"


def extract(element):
    lst = [r for r in map(dictize, element) if isinstance(r[0], str)]
    for key in LIST_KEYS:
        values = [v for k, v in [r for r in lst if r[0] == key]]
        if values:
            lst = [r for r in lst if r[0] != key] + [(key, values)]
    return lst


def dictize(element):
    return element.tag, OrderedDict(extract(element)) or element.text


class MaafBackend(BaseBackend):
    display_name = "MAAF"
    verify_ssl = False

    def inner_harvest(self):
        """Parse the index pages HTML to find link to dataset descriptors"""
        directories = [self.source.url]
        while directories:
            directory = directories.pop(0)
            response = self.get(directory)
            root = html.fromstring(response.text)
            for link in root.xpath("//ul/li/a")[1:]:  # Skip parent directory.
                href = link.get("href")
                if href.endswith("/"):
                    directories.append(urljoin(directory, href))
                elif href.lower().endswith(".xml"):
                    # We use the URL as `remote_id` for now, we'll be replace at
                    # the beginning of the process
                    self.process_dataset(urljoin(directory, href))
                    if self.has_reached_max_items():
                        return
                else:
                    log.debug("Skip %s", href)

    def inner_process_dataset(self, item: HarvestItem):
        response = self.get(item.remote_id)
        xml = self.parse_xml(response.content)
        metadata = xml["metadata"]

        # Replace the `remote_id` from the URL to `id`.
        item.remote_id = metadata["id"]
        dataset = self.get_dataset(item.remote_id)

        dataset.title = metadata["title"]
        dataset.frequency = FREQUENCIES.get(metadata["frequency"], "unknown")
        dataset.description = metadata["notes"]
        dataset.private = metadata["private"]
        dataset.tags = sorted(set(metadata["tags"]))

        if metadata.get("license_id"):
            dataset.license = License.objects.get(id=metadata["license_id"])

        if metadata.get("temporal_coverage_from") and metadata.get("temporal_coverage_to"):
            dataset.temporal_coverage = db.DateRange(
                start=metadata["temporal_coverage_from"], end=metadata["temporal_coverage_to"]
            )

        if metadata.get("territorial_coverage_code") or metadata.get(
            "territorial_coverage_granularity"
        ):
            dataset.spatial = SpatialCoverage()

            if metadata.get("territorial_coverage_granularity"):
                dataset.spatial.granularity = GRANULARITIES.get(
                    metadata["territorial_coverage_granularity"]
                )

            if metadata.get("territorial_coverage_code"):
                dataset.spatial.zones = [ZONES[metadata["territorial_coverage_code"]]]

        dataset.resources = []
        cle = get_by(metadata["resources"], "format", "cle")
        for row in metadata["resources"]:
            if row["format"] == "cle":
                continue
            else:
                resource = Resource(
                    title=row["name"],
                    description=(row["description"] + "\n\n" + SSL_COMMENT).strip(),
                    filetype="remote",
                    url=row["url"],
                    format=row["format"],
                )
                if resource.format == "csv" and cle:
                    resource.checksum = Checksum(type="sha256", value=self.get(cle["url"]).text)
                if row.get("last_modified"):
                    resource.last_modified_internal = row["last_modified"]
                dataset.resources.append(resource)

        if metadata.get("author"):
            dataset.extras["author"] = metadata["author"]
        if metadata.get("author_email"):
            dataset.extras["author_email"] = metadata["author_email"]
        if metadata.get("maintainer"):
            dataset.extras["maintainer"] = metadata["maintainer"]
        if metadata.get("maintainer_email"):
            dataset.extras["maintainer_email"] = metadata["maintainer_email"]
        for extra in metadata["extras"]:
            dataset.extras[extra["key"]] = extra["value"]

        return dataset

    def parse_xml(self, xml):
        root = etree.fromstring(xml)
        self.xsd.validate(root)
        _, tree = dictize(root)
        return self.validate(tree, schema)

    @property
    def xsd(self):
        if not getattr(self, "_xsd", None):
            with open(XSD_PATH) as f:
                doc = etree.parse(f)
            self._xsd = etree.XMLSchema(doc)
        return self._xsd
