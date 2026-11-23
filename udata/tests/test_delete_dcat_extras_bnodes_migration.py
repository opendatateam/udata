from dataclasses import dataclass, field

import pytest
from mongoengine.connection import get_db
from rdflib import BNode

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Dataset, Resource
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import argvalues

MIGRATION = "2026-11-20-delete-dcat-extras-bnodes.py"

BNODE_ID = str(BNode())
SAME = object()


@dataclass
class Fields:
    base_str: list[str] = field(default_factory=list)
    base_array: list[str] = field(default_factory=list)
    dcat_str: list[str] = field(default_factory=list)
    dcat_array: list[str] = field(default_factory=list)
    canary_str: tuple[str, str] | None = None
    canary_array: tuple[str, str] | None = None


DATASET_FIELDS = Fields(
    dcat_str=["spatial_resolution"],
    dcat_array=["license", "accessRights", "rights", "provenance"],
    canary_str=("title", BNODE_ID),
    canary_array=("tags", [BNODE_ID.lower()]),  # tags are automatically lowercased
)

RESOURCE_FIELDS = Fields(
    base_str=["format", "mime"],
    dcat_array=["license", "accessRights", "rights"],
    canary_str=("title", BNODE_ID),
    # no available canary_array field in Resource
)


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def get_dataset(dataset_id) -> Dataset:
    return Dataset.objects(id=dataset_id).first()


def get_resource(dataset_id, resource_index=0) -> Resource:
    return get_dataset(dataset_id)["resources"][resource_index]


def to_dict(obj: Dataset | Resource):
    return dict(obj.to_mongo().items())


def fake_fields(fields: Fields, value: str | list | None):
    if isinstance(value, str):  # applies to both str and array
        str_value, array_value = value, [value]
    else:  # isinstance(list) => apply only to array
        str_value, array_value = None, value

    return {
        # base fields, always set even when None, to override Factory default
        **{f: str_value for f in fields.base_str},
        **{f: array_value for f in fields.base_array},
        "extras": {
            "dcat": {
                # extras fields, only set when not None, as Factory doesn't initialize anything
                **({f: str_value for f in fields.dcat_str} if str_value else {}),
                **({f: array_value for f in fields.dcat_array} if array_value else {}),
                "canary_dcat_str": BNODE_ID,
                "canary_dcat_array": [BNODE_ID],
            },
            "canary_extras_str": BNODE_ID,
            "canary_extras_array": [BNODE_ID],
        },
        # canary base fields, always set to value from *_FIELDS def, to override Factory default
        **({c[0]: c[1]} if (c := fields.canary_str) else {}),
        **({c[0]: c[1]} if (c := fields.canary_array) else {}),
    }


def assert_migrated(actual: Dataset | Resource, fields: Fields, value: str | list | None):
    expected = fake_fields(fields, value)

    for base in ["base_str", "base_array"]:
        for f in getattr(fields, base) or []:
            assert getattr(actual, f) == expected.get(f)

    for canary in ["canary_str", "canary_array"]:
        if c := getattr(fields, canary):
            assert getattr(actual, c[0]) == expected.get(c[0])

    assert actual.extras == expected.get("extras")


class MigrationTest(PytestOnlyDBTestCase):
    ARGVALUES = argvalues(
        [
            # cases that apply to both str and array (array obtained by wrapping str in llist)
            (BNODE_ID, None, "match-standard"),
            (BNODE_ID.lower(), None, "match-lowercase"),
            ("whatever", SAME, "no-match"),
            (BNODE_ID.upper(), SAME, "no-match-uppercase"),
            ("X" + BNODE_ID[1:], SAME, "no-match-no-prefix"),
            (BNODE_ID[:31], SAME, "no-match-too-short"),
            (BNODE_ID + "a", SAME, "no-match-too-long"),
            (BNODE_ID + "z", SAME, "no-match-not-hex"),
            # cases that apply to array fields only
            (["foo", BNODE_ID, "bar"], ["foo", "bar"], "list-preserve-other"),
            ([BNODE_ID, BNODE_ID.lower()], None, "list-multiple-match"),
        ]
    )

    def test_migration_nothing_to_do(self):
        dataset = DatasetFactory(
            resources=[ResourceFactory(), ResourceFactory()],
            extras={"foo": "bar"},
        )
        d_before = get_dataset(dataset.id)
        r_before = [get_resource(dataset.id, i) for i in range(len(dataset.resources))]

        migrate()

        assert to_dict(d_before) == to_dict(get_dataset(dataset.id))
        for i in range(len(dataset.resources)):
            assert to_dict(r_before[i]) == to_dict(get_resource(dataset.id, i))

    @pytest.mark.parametrize("value, expected", ARGVALUES)
    def test_migration_dataset(self, value, expected):
        dataset = DatasetFactory(**fake_fields(DATASET_FIELDS, value))
        d_before = get_dataset(dataset.id)

        migrate()

        d = get_dataset(dataset.id)
        if expected is SAME:
            assert to_dict(d_before) == to_dict(d)
        else:
            assert to_dict(d_before) != to_dict(d)
            assert_migrated(d, DATASET_FIELDS, expected)

    @pytest.mark.parametrize("value, expected", ARGVALUES)
    def test_migration_resources(self, value, expected):
        dataset = DatasetFactory(
            resources=[
                ResourceFactory(**fake_fields(RESOURCE_FIELDS, value)),
                ResourceFactory(**fake_fields(RESOURCE_FIELDS, "canary")),
                ResourceFactory(**fake_fields(RESOURCE_FIELDS, value)),
            ]
        )
        r_before = [get_resource(dataset.id, i) for i in range(len(dataset.resources))]

        migrate()

        r = get_resource(dataset.id, 1)  # canary
        assert to_dict(r_before[1]) == to_dict(r)

        for idx in [0, 2]:
            r = get_resource(dataset.id, idx)
            if expected is SAME:
                assert to_dict(r_before[idx]) == to_dict(r)
            else:
                assert to_dict(r_before[idx]) != to_dict(r)
                assert_migrated(r, RESOURCE_FIELDS, expected)

    def test_migration_idempotent(self):
        dataset = DatasetFactory(
            **fake_fields(DATASET_FIELDS, BNODE_ID),
            resources=[ResourceFactory(**fake_fields(RESOURCE_FIELDS, BNODE_ID))],
        )
        before = get_dataset(dataset.id)

        migrate()
        first_run = get_dataset(dataset.id)
        assert to_dict(before) != to_dict(first_run)

        migrate()
        second_run = get_dataset(dataset.id)
        assert to_dict(first_run) == to_dict(second_run)
