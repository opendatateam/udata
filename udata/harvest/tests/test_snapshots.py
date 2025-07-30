import json
import os
import xml.etree.ElementTree as ET
from os.path import dirname, isfile, join

import pytest
import requests_mock
from deepdiff import DeepDiff

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
]


@pytest.mark.usefixtures("clean_db")
@pytest.mark.options(PLUGINS=["dcat"])
class SnapshotsTest:
    @pytest.mark.parametrize("harvester_conf", harvester_configs)
    def test_all(self, harvester_conf):
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

        harvester = HarvestSourceFactory(
            backend=harvester_conf["backend"], url=harvester_conf["url"]
        )

        data = {}
        data_path = join(
            SNAPSHOTS_DIR,
            f"{harvester.backend}-{harvester.url.replace('://', '_').replace('/', '_')}.json",
        )
        refresh = not isfile(data_path) or os.getenv("REFRESH_SNAPSHOTS", False)

        if not refresh:
            data = json.load(open(data_path))

        with MyMock(real_http=True) as m:
            if not refresh:
                for history in data["requests_history"]:
                    m.register_uri(
                        method=history["request"]["method"],
                        url=history["request"]["url"],
                        text=history["response"]["body"],
                        status_code=history["response"]["status_code"],
                        headers=history["response"]["headers"],
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

            for index, graph in enumerate(data["job"]["data"]["graphs"]):
                diff = main.diff_texts(
                    graph.encode("utf-8"),
                    new_data["job"]["data"]["graphs"][index].encode("utf-8"),
                    formatter=formatting.DiffFormatter(),
                )
                print(f"\n\n{graph}\n\n")
                print(f"\n\n{new_data['job']['data']['graphs'][index]}\n\n")

                assert compare_xml(graph, new_data["job"]["data"]["graphs"][index])

            diff = DeepDiff(
                data,
                # Compare datetime as strings by serialize/deserialize
                json.loads(json.dumps(new_data, indent=2, default=str)),
                verbose_level=2,
                exclude_regex_paths=[
                    r"root\['requests_history'\]",
                    r"_id",
                    r"id",
                    r"created_at_internal",
                    r"last_modified_internal",
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
                ],
            )

            print(diff.pretty())
            print(diff)
            assert not diff


def sort_children(elem):
    # Trie les enfants par balise + attributs + texte pour stabilité
    elem[:] = sorted(elem, key=lambda e: (e.tag, sorted(e.attrib.items()), (e.text or "").strip()))
    for child in elem:
        sort_children(child)


def elements_equal(e1, e2):
    if e1.tag != e2.tag:
        return False
    if sorted(e1.attrib.items()) != sorted(e2.attrib.items()):
        return False
    if (e1.text or "").strip() != (e2.text or "").strip():
        return False
    if len(e1) != len(e2):
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
                        "body": request.body.decode()
                        if request.body and hasattr(request.body, "decode")
                        else str(request.body),
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
