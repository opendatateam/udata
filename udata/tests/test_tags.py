import logging
from io import StringIO

import pytest
from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.tags.models import Tag
from udata.core.tags.tasks import count_tags
from udata.frontend import csv
from udata.tags import normalize, slug, tags_list
from udata.tests.helpers import assert200

log = logging.getLogger(__name__)


MAX_TAG_LENGTH = 32


@pytest.mark.frontend
class TagsTests:
    modules = ["core.tags"]

    def test_csv(self, client):
        Tag.objects.create(name="datasets-only", counts={"datasets": 15})
        Tag.objects.create(name="reuses-only", counts={"reuses": 10})
        Tag.objects.create(name="both", counts={"reuses": 10, "datasets": 15})

        response = client.get(url_for("tags.csv"))
        assert200(response)
        assert response.mimetype == "text/csv"
        assert response.charset == "utf-8"

        csvfile = StringIO(response.data.decode("utf8"))
        reader = reader = csv.get_reader(csvfile)
        header = next(reader)
        rows = list(reader)

        assert header == ["name", "datasets", "reuses", "total"]
        assert len(rows) == 3
        assert rows[0] == ["both", "15", "10", "25"]
        assert rows[1] == ["datasets-only", "15", "0", "15"]
        assert rows[2] == ["reuses-only", "0", "10", "10"]

    def test_count(self):
        for i in range(1, 4):
            # Tags should be normalized and deduplicated.
            tags = ['Tag "{0}"'.format(j) for j in range(i)] + ["tag-0"]
            DatasetFactory(tags=tags, visible=True)
            ReuseFactory(tags=tags, visible=True)

        count_tags.run()

        expected = {
            "tag-0": 3,
            "tag-1": 2,
            "tag-2": 1,
        }

        assert len(Tag.objects) == len(expected)

        for name, count in expected.items():
            tag = Tag.objects.get(name=name)
            assert tag.total == 2 * count
            assert tag.counts["datasets"] == count
            assert tag.counts["reuses"] == count


class TagsUtilsTest:
    def test_tags_list(self):
        assert tags_list("") == []
        assert tags_list("a") == ["a"]
        assert sorted(tags_list("a, b, c")) == ["a", "b", "c"]
        assert sorted(tags_list("a b, c d, e")) == ["a-b", "c-d", "e"]

    def test_tags_list_strip(self):
        assert sorted(tags_list("a, b ,  ,,, c")) == ["a", "b", "c"]
        assert sorted(tags_list("  a b ,  c   d, e ")) == ["a-b", "c-d", "e"]

    def test_tags_list_deduplication(self):
        assert sorted(tags_list("a b, c d,  a  b , e")) == ["a-b", "c-d", "e"]

    def test_slug_empty(self):
        assert slug("") == ""

    def test_slug_several_words(self):
        assert slug("la claire fontaine") == "la-claire-fontaine"

    def test_slug_accents(self):
        assert slug("école publique") == "ecole-publique"

    def test_slug_case(self):
        assert slug("EcoLe publiquE") == "ecole-publique"

    def test_slug_consecutive_spaces(self):
        assert slug("ecole  publique") == "ecole-publique"

    def test_slug_special_characters(self):
        assert slug("ecole-publique") == "ecole-publique"
        assert slug("ecole publique.") == "ecole-publique"
        assert slug("ecole publique-") == "ecole-publique"
        assert slug("ecole publique_") == "ecole-publique"

    @pytest.mark.options(TAG_MAX_LENGTH=MAX_TAG_LENGTH)
    def test_normalize(self, app):
        assert normalize("") == ""
        assert normalize("a") == ""
        assert normalize("aa") == ""
        assert normalize("aaa") == "aaa"
        assert normalize("a" * (MAX_TAG_LENGTH + 1)) == "a" * MAX_TAG_LENGTH
        assert normalize("aAa a") == "aaa-a"
