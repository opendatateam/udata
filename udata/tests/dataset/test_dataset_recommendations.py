import jsonschema
import pytest

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.recommendations import recommendations_add, recommendations_clean
from udata.core.reuse.factories import ReuseFactory

MOCK_URL = "http://reco.net"


@pytest.fixture
def datasets():
    return DatasetFactory.create_batch(3)


@pytest.fixture
def reuses():
    return ReuseFactory.create_batch(2)


@pytest.fixture
def mock_invalid_response():
    return [{"foo": "bar"}]


@pytest.fixture
def mock_response(datasets, reuses):
    ds1, ds2, ds3 = datasets
    r1, r2 = reuses
    return [
        {
            # Invalid ID, but valid reco: should not crash the command
            "id": "1",
            "recommendations": [{"id": str(ds1.id), "score": 50}],
        },
        {
            # valid ID and recos,
            # should process two elements w/o crashing
            # should reorder by score and handle reco by ID and slug
            "id": str(ds2.id),
            "recommendations": [
                {"id": str(ds3.id), "score": 1},
                {"id": str(ds1.slug), "score": 2},
                {"id": "nope", "score": 50},
                {
                    "id": str(r1.slug),
                    "score": 50,
                    "type": "reuse",
                },
                {
                    "id": str(r2.id),
                    "score": 100,
                    "type": "reuse",
                },
            ],
        },
        {
            # Valid ID but recommended dataset does not exist
            "id": str(ds3.id),
            "recommendations": [
                {"id": "nope", "score": 50},
            ],
        },
    ]


@pytest.mark.usefixtures("clean_db")
class DatasetRecommendationsTest:
    def test_clean(self):
        ds1 = DatasetFactory(
            extras={
                "untouched": "yep",
                "recommendations:sources": ["foo", "bar"],
                "recommendations": [
                    {"id": "id1", "source": "bar", "score": 50},
                    {"id": "id2", "source": "foo", "score": 50},
                ],
            }
        )
        ds2 = DatasetFactory(
            extras={
                "wait": "for it",
                "recommendations:sources": ["baz"],
                "recommendations": [
                    {"id": "id2", "source": "baz", "score": 50},
                ],
            }
        )

        recommendations_clean()

        ds1.reload()
        ds2.reload()

        assert ds1.extras == {"untouched": "yep"}
        assert ds2.extras == {"wait": "for it"}

    def test_datasets_recommendations_invalid_data_in_config(self, mock_invalid_response, rmock):
        rmock.get(MOCK_URL, json=mock_invalid_response)

        with pytest.raises(jsonschema.exceptions.ValidationError):
            recommendations_add({"fake_source": MOCK_URL}, should_clean=False)

    def test_datasets_recommendations_from_config_empty_db(self, rmock, mock_response, datasets):
        ds1, ds2, ds3 = datasets
        rmock.get(MOCK_URL, json=mock_response)

        recommendations_add({"fake_source": MOCK_URL}, should_clean=False)

        # Correct recommendations have been filled
        ds2.reload()
        assert ds2.extras["recommendations:sources"] == ["fake_source"]
        assert ds2.extras["recommendations"] == [
            {"id": str(ds1.id), "source": "fake_source", "score": 2},
            {"id": str(ds3.id), "source": "fake_source", "score": 1},
        ]

        # Invalid recommendations have not been filled
        ds1.reload()
        ds3.reload()
        assert ds1.extras == {}
        assert ds3.extras == {}

    def test_datasets_recommendations_from_config(self, rmock, mock_response, datasets, reuses):
        ds1, ds2, ds3 = datasets
        r1, r2 = reuses
        ds4 = DatasetFactory()
        rmock.get(MOCK_URL, json=mock_response)
        ds2.extras["recommendations:sources"] = ["existing"]
        ds2.extras["recommendations"] = [
            {"id": str(ds4.id), "source": "existing", "score": 50},
        ]
        ds2.save()

        recommendations_add({"fake_source": MOCK_URL}, should_clean=False)

        # Recommendations have been merged, new source has been added
        ds2.reload()
        assert set(ds2.extras["recommendations:sources"]) == set(["existing", "fake_source"])
        assert ds2.extras["recommendations"] == [
            {"id": str(ds4.id), "source": "existing", "score": 50},
            {"id": str(ds1.id), "source": "fake_source", "score": 2},
            {"id": str(ds3.id), "source": "fake_source", "score": 1},
        ]
        assert ds2.extras["recommendations-reuses"] == [
            {"id": str(r2.id), "source": "fake_source", "score": 100},
            {"id": str(r1.id), "source": "fake_source", "score": 50},
        ]

    def test_datasets_recommendations_from_config_clean(self, mock_response, rmock, datasets):
        ds1, ds2, ds3 = datasets
        rmock.get(MOCK_URL, json=mock_response)

        ds1.extras["recommendations:sources"] = ["fake_source"]
        ds1.extras["recommendations"] = [{"id": str(ds2.id), "source": "fake_source", "score": 100}]
        ds1.save()

        recommendations_add({"fake_source": MOCK_URL}, should_clean=True)

        # Correct recommendations have been filled
        ds2.reload()
        assert ds2.extras["recommendations:sources"] == ["fake_source"]
        assert ds2.extras["recommendations"] == [
            {"id": str(ds1.id), "source": "fake_source", "score": 2},
            {"id": str(ds3.id), "source": "fake_source", "score": 1},
        ]

        # Previous recommendations have been cleaned
        ds1.reload()
        assert ds1.extras == {}

    def test_datasets_recommendations_ignore_self_recommendation(self, rmock, datasets):
        ds1, _, _ = datasets
        rmock.get(
            MOCK_URL,
            json=[{"id": str(ds1.id), "recommendations": [{"id": str(ds1.id), "score": 50}]}],
        )

        recommendations_add({"fake_source": MOCK_URL}, should_clean=True)

        ds1.reload()
        assert ds1.extras == {}

    def test_datasets_recommendations_ignore_duplicate_recommendation(self, rmock, datasets):
        ds1, ds2, ds3 = datasets
        ds1.extras = {"recommendations": [{"id": str(ds2), "source": "fake_source", "score": 1}]}
        rmock.get(
            MOCK_URL,
            json=[
                {
                    "id": str(ds1.id),
                    "recommendations": [
                        {"id": str(ds2.id), "score": 4},
                        {"id": str(ds3.id), "score": 5},
                    ],
                }
            ],
        )

        recommendations_add({"fake_source": MOCK_URL}, should_clean=True)

        # The new recommendation score for ds2 will be kept instead of the old one
        ds1.reload()
        assert ds1.extras["recommendations"] == [
            {"id": str(ds3.id), "source": "fake_source", "score": 5},
            {"id": str(ds2.id), "source": "fake_source", "score": 4},
        ]
