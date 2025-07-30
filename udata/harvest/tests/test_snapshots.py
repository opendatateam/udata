import json
import os
import xml.etree.ElementTree as ET
from os.path import dirname, isfile, join

import pytest
import requests_mock
from deepdiff import DeepDiff
from pyld import jsonld
from rdflib import Graph

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.harvest import actions
from udata.harvest.models import HarvestJob
from udata.harvest.tests.factories import HarvestSourceFactory

SNAPSHOTS_DIR = join(dirname(__file__), "snapshots")


harvester_configs = [
    {
        "backend": "dcat",
        "url": "https://data.capatlantique.fr/api/explore/v2.1/catalog/exports/dcat/?where=publisher%3D%22CCAS+Gu%C3%A9rande%22&include_exports=json%2Ccsv%2Cshp%2Cgeojson&lang=fr",
    },
    {
        "backend": "csw-iso-19139",
        "url": "https://ogc.geo-ide.developpement-durable.gouv.fr/csw/csw-ddt24",
    },
    {
        "backend": "ckan",
        "url": "https://www.datasud.fr/fr/indexer/service/ckan/",
        "config": {
            "filters": [
                {
                    "key": "organization",
                    "value": '"communaute-dagglomeration-de-gap-tallard-durance"',
                },
            ],
        },
    },
]


@pytest.mark.usefixtures("clean_db")
@pytest.mark.options(PLUGINS=["dcat", "csw-iso-19139", "ckan"])
class SnapshotsTest:
    @pytest.mark.parametrize("harvester_conf", harvester_configs)
    def test_all(self, harvester_conf):
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

        harvester = HarvestSourceFactory(
            backend=harvester_conf["backend"],
            url=harvester_conf["url"],
            config=harvester_conf.get("config", {}),
        )

        data = {}
        data_path = join(
            SNAPSHOTS_DIR,
            f"{harvester.backend}-{harvester.url.replace('://', '_').replace('/', '_')}.json",
        )
        refresh = not isfile(data_path) or os.getenv("REFRESH_SNAPSHOTS", False)

        if not refresh:
            data = json.load(open(data_path))

        def match_body(request, history):
            return parse_request_body(request.text) == history["request"]["body"]

        def make_matcher(history):
            return lambda request: match_body(request, history)

        with MyMock(real_http=refresh) as m:
            if not refresh:
                for history in data["requests_history"]:
                    history["response"]["headers"].pop("Content-Encoding", None)
                    m.register_uri(
                        method=history["request"]["method"],
                        url=history["request"]["url"],
                        text=history["response"]["body"],
                        status_code=history["response"]["status_code"],
                        headers=history["response"]["headers"],
                        additional_matcher=make_matcher(history),
                    )

            actions.run(harvester.slug)

        assert HarvestJob.objects.count() == 1

        new_data = {
            "requests_history": m.history,
            "job": HarvestJob.objects[0].to_dict(),
            "datasets": [d.to_dict() for d in Dataset.objects],
            "dataservices": [d.to_dict() for d in Dataservice.objects],
        }

        if refresh:
            json.dump(new_data, open(data_path, "w"), indent=2, default=str)
        else:
            from xmldiff import formatting, main

            if "graphs" in data["job"]["data"]:
                for index, graph in enumerate(data["job"]["data"]["graphs"]):
                    diff = main.diff_texts(
                        graph.encode("utf-8"),
                        new_data["job"]["data"]["graphs"][index].encode("utf-8"),
                        formatter=formatting.DiffFormatter(),
                    )
                    print(graph, file=open("/tmp/1.xml", "w"))
                    print(new_data["job"]["data"]["graphs"][index], file=open("/tmp/2.xml", "w"))
                    print(f"\n\n{graph}\n\n")
                    print(f"\n\n{new_data['job']['data']['graphs'][index]}\n\n")

                    assert compare_rdf_graphs_canonically(
                        graph, new_data["job"]["data"]["graphs"][index]
                    ), "RDF graphs are differents"

            diff = DeepDiff(
                data,
                # Compare datetime as strings by serialize/deserialize
                json.loads(json.dumps(new_data, indent=2, default=str)),
                verbose_level=2,
                ignore_order=True,
                exclude_regex_paths=[
                    r"root\['requests_history'\]",
                    r"_id",
                    r"id",
                    r"created_at_internal",
                    r"last_modified_internal",
                    r"last_update",
                    r"root\['datasets'\]\[\d+]\['harvest'\]\['last_update'\]",
                    r"root\['dataservices'\]\[\d+]\['harvest'\]\['last_update'\]",
                    r"root\['dataservices'\]\[\d+]\['created_at'\]",
                    r"root\['dataservices'\]\[\d+]\['metadata_modified_at'\]",
                    r"root\['dataservices'\]\[\d+]\['datasets'\]",
                    r"\['created'\]",
                    r"\['started'\]",
                    r"\['ended'\]",
                    r"root\['job'\]\['data'\]\['graphs'\]",
                    r"root\['job'\]\['items'\]\[\d+\]\['dataset'\]",
                    r"root\['job'\]\['items'\]\[\d+\]\['dataservice'\]",
                    r"root\['job'\]\['source'\]",
                    r"root\['job'\]\['items'\]\[\d+\]\['errors'\]\[\d+\]\['created_at'\]",
                ],
            )

            print(diff.pretty())
            print(diff)
            assert not diff, "Global diffs are different"


def rdf_to_canonical_jsonld(xml_string: str) -> str:
    g = Graph()
    g.parse(data=xml_string, format="application/rdf+xml")
    jsonld_data = g.serialize(format="json-ld", indent=2)

    # Parse to dict and canonicalize
    doc = json.loads(jsonld_data)
    canon = jsonld.normalize(doc, {"algorithm": "URDNA2015", "format": "application/n-quads"})

    return canon


def compare_rdf_graphs_canonically(xml1: str, xml2: str) -> bool:
    canon1 = rdf_to_canonical_jsonld(xml1)
    canon2 = rdf_to_canonical_jsonld(xml2)
    return canon1 == canon2


def normalize_rdf(xml_string: str) -> str:
    g = Graph()
    g.parse(data=xml_string, format="application/rdf+xml")
    return "\n".join(sorted(g.serialize(format="nt").splitlines()))


def compare_rdf_graphs(xml1: str, xml2: str) -> bool:
    norm1 = normalize_rdf(xml1)
    norm2 = normalize_rdf(xml2)
    return norm1 == norm2


def get_attributes(e):
    return sorted(
        {
            k: v
            for k, v in e.attrib.items()
            if str(k) == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}nodeID"
        }
    )


def sort_children(elem):
    # Trie les enfants par balise + attributs + texte pour stabilité
    elem[:] = sorted(elem, key=lambda e: (e.tag, get_attributes(e), (e.text or "").strip()))
    for child in elem:
        sort_children(child)


def elements_equal(e1, e2):
    if e1.tag != e2.tag:
        print(f"Tag are different: {e1.tag} != {e2.tag}")
        return False
    if get_attributes(e1) != get_attributes(e2):
        print("Attributes are different:")
        print(get_attributes(e1))
        print(get_attributes(e2))
        return False
    if (e1.text or "").strip() != (e2.text or "").strip():
        print("Text are different:")
        print((e1.text or "").strip())
        print((e2.text or "").strip())
        return False
    if len(e1) != len(e2):
        print(f"Length is different: {len(e1)} != {len(e2)}")
        return False
    for c1, c2 in zip(e1, e2):
        if not elements_equal(c1, c2):
            return False
    return True


def compare_xml(xml1_str, xml2_str):
    root1 = ET.fromstring(xml1_str)
    root2 = ET.fromstring(xml2_str)
    sort_children(root1)
    sort_children(root2)
    return elements_equal(root1, root2)


class MyMock(requests_mock.Mocker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = []
        real_send = self._mock_target.send

        def send(session, request, **kwargs):
            response = real_send(session, request, **kwargs)
            self.history.append(
                {
                    "request": {
                        "method": request.method,
                        "url": request.url,
                        "headers": dict(request.headers),
                        "body": parse_request_body(request.body),
                    },
                    "response": {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response.text,
                    },
                }
            )
            return response

        self._mock_target.send = send


def parse_request_body(body):
    if body is None:
        return None

    return body.decode() if body and hasattr(body, "decode") else str(body)
