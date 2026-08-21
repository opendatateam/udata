from io import BytesIO
from unittest import mock

from flask import url_for
from mongoengine.context_managers import query_counter

from udata.core import storages
from udata.core.access_type.constants import AccessAudienceCondition, AccessAudienceType
from udata.core.access_type.models import AccessAudience
from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DataservicesListBloc,
    DatasetsListBloc,
    ReusesListBloc,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import (
    assert200,
    assert201,
    assert204,
    assert400,
    assert403,
    assert404,
    create_test_image,
)


class PostsAPITest(APITestCase):
    def test_post_api_list(self):
        """It should fetch a post list from the API"""
        PostFactory.create_batch(3)
        draft = PostFactory(published=None)

        response = self.get(url_for("api.posts"))
        assert200(response)
        # Response should not contain the unpublished post
        assert len(response.json["data"]) == 3

        self.login(AdminFactory())

        response = self.get(url_for("api.posts"))
        assert200(response)

        assert len(response.json["data"]) == 3
        assert str(draft.id) not in [post["id"] for post in response.json["data"]]

        response = self.get(url_for("api.posts", with_drafts=True))
        assert200(response)

        assert len(response.json["data"]) == 4
        assert str(draft.id) in [post["id"] for post in response.json["data"]]

    def test_post_api_list_excludes_blocs(self):
        """Blocs should not be included in the list endpoint"""
        bloc = DatasetsListBloc(title="Test", datasets=[])
        PostFactory(body_type="blocs", blocs=[bloc])

        response = self.get(url_for("api.posts"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert "blocs" not in response.json["data"][0]

    def test_post_api_get_blocs_no_n_plus_1(self):
        """Fetching a blocs page must not dereference references one by one.

        Each card (dataset/reuse/dataservice) embeds its organization. Without
        batching, every card triggers its own organization query, so the query
        count scales with the number of cards (hundreds on real pages). The
        `prefetch_blocs_references` helper must keep it flat.
        """
        orgs = OrganizationFactory.create_batch(4)

        def query_count(cards_per_bloc):
            def datasets():
                return [
                    DatasetFactory(organization=orgs[i % len(orgs)]) for i in range(cards_per_bloc)
                ]

            # Datasets spread across 4 top-level blocs + 2 blocs nested in an accordion.
            top_level = [DatasetsListBloc(title=f"Top {i}", datasets=datasets()) for i in range(4)]
            accordion = AccordionListBloc(
                title="Accordion",
                items=[
                    AccordionItemBloc(
                        title=f"Item {i}",
                        content=[DatasetsListBloc(title=f"Nested {i}", datasets=datasets())],
                    )
                    for i in range(2)
                ],
            )
            reuses = [ReuseFactory(organization=orgs[i % len(orgs)]) for i in range(cards_per_bloc)]
            dataservices = [
                DataserviceFactory(organization=orgs[i % len(orgs)]) for i in range(cards_per_bloc)
            ]
            blocs = top_level + [
                accordion,
                ReusesListBloc(title="Reuses", reuses=reuses),
                DataservicesListBloc(title="Dataservices", dataservices=dataservices),
            ]
            post = PostFactory(body_type="blocs", content=None, blocs=blocs, datasets=[], reuses=[])

            url = url_for("api.post", post=post)
            assert200(self.get(url))  # warm up one-time queries

            with query_counter() as counter:
                response = self.get(url)
                count = int(counter)
            assert200(response)

            # A reference the prefetch fails to resolve silently drops from the list —
            # which *lowers* the query count. Assert every card is there, with its
            # organization resolved, so a flat count really means "batched".
            org_ids = {str(o.id) for o in orgs}
            by_class = {}
            for bloc in response.json["blocs"]:
                by_class.setdefault(bloc["class"], []).append(bloc)
            accordion_items = by_class["AccordionListBloc"][0]["items"]
            dataset_blocs = by_class["DatasetsListBloc"] + [
                item["content"][0] for item in accordion_items
            ]
            assert len(dataset_blocs) == 6  # 4 top-level + 2 nested in the accordion
            cards = [card for bloc in dataset_blocs for card in bloc["datasets"]]
            cards += by_class["ReusesListBloc"][0]["reuses"]
            cards += by_class["DataservicesListBloc"][0]["dataservices"]
            assert len(cards) == cards_per_bloc * 8
            for card in cards:
                assert card["organization"]["id"] in org_ids

            return count

        many, few = query_count(5), query_count(1)
        assert many == few, (
            f"the query count grows with the number of cards ({many} for 5 cards per "
            f"bloc, {few} for 1): the references are dereferenced one by one"
        )

    def test_post_api_blocs_projection_keeps_output_intact(self):
        """Projecting out heavy unused fields must not change the serialized cards.

        `prefetch_blocs_references` loads each card without the list fields no card
        mask serializes (a dataset's `resources` can hold dozens of sub-documents —
        deserializing them dominates the response time). The output must stay
        identical to a full-document load; this locks against projecting out a field
        a card actually needs.

        Every entry of `CARD_UNUSED_HEAVY_FIELDS` is populated here, on each model
        that owns it: an empty field serializes the same whether it was projected out
        or not, so the comparison would hold without checking anything.
        """
        org = OrganizationFactory()
        contact_point = ContactPointFactory(role="contact", organization=org)
        audiences = [
            AccessAudience(role=AccessAudienceType.COMPANY, condition=AccessAudienceCondition.YES)
        ]

        datasets = [
            DatasetFactory(
                organization=org,
                nb_resources=8,
                contact_points=[contact_point],
                access_audiences=audiences,
            )
            for _ in range(3)
        ]
        dataservices = [
            DataserviceFactory(
                organization=org,
                datasets=datasets,
                contact_points=[contact_point],
                access_audiences=audiences,
            )
            for _ in range(2)
        ]
        reuses = [
            ReuseFactory(organization=org, datasets=datasets, dataservices=dataservices)
            for _ in range(2)
        ]
        post = PostFactory(
            body_type="blocs",
            content=None,
            blocs=[
                DatasetsListBloc(title="Datasets", datasets=datasets),
                ReusesListBloc(title="Reuses", reuses=reuses),
                DataservicesListBloc(title="Dataservices", dataservices=dataservices),
            ],
            datasets=[],
            reuses=[],
        )
        url = url_for("api.post", post=post)

        projected = self.get(url).json

        # Same request, but loading the full documents (no field projection).
        with mock.patch("udata.core.edito_blocs.base.CARD_UNUSED_HEAVY_FIELDS", ()):
            full = self.get(url).json

        assert projected["blocs"] == full["blocs"]
        # `quality` carries resource-derived criteria: the card reads them from the
        # stored cache, which is why `resources` can be dropped from the load.
        card = projected["blocs"][0]["datasets"][0]
        assert card["quality"]["has_resources"] is True

    def test_post_api_blocs_preserve_reference_order(self):
        """Batch-loading a bloc's references must not reorder its cards.

        `id__in` returns the documents in the model's default order (`Dataset` sorts
        by `-created_at_internal`), not in the order of the reference list, so the
        prefetch reorders them from the stored references. Bloc lists are editorial
        content: their order is the behaviour.
        """
        created = [DatasetFactory() for _ in range(6)]
        # Interleaved, so the list order matches neither the creation order nor its
        # reverse — the two orders a batch query can return on its own.
        datasets = created[::2] + created[1::2]
        post = PostFactory(
            body_type="blocs",
            content=None,
            blocs=[DatasetsListBloc(title="Ordered", datasets=datasets)],
            datasets=[],
            reuses=[],
        )

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        cards = response.json["blocs"][0]["datasets"]
        assert [card["id"] for card in cards] == [str(dataset.id) for dataset in datasets]

    def test_post_list_does_not_dereference_blocs(self):
        """The list endpoint masks out blocs, so it must not dereference them.

        Blocs are excluded from `/posts` via the page mask. Dereferencing their
        references (datasets, organizations…) here would add latency for data that
        is never serialized, so the query count must not grow with the bloc contents.
        """
        org = OrganizationFactory()
        post = PostFactory(body_type="blocs", content=None, blocs=[], datasets=[], reuses=[])

        def query_count(nb_cards):
            post.blocs = [
                DatasetsListBloc(
                    title="Heavy",
                    datasets=[DatasetFactory(organization=org) for _ in range(nb_cards)],
                )
            ]
            post.save()

            url = url_for("api.posts")
            assert200(self.get(url))  # warm up one-time queries

            with query_counter() as counter:
                response = self.get(url)
                count = int(counter)
            assert200(response)
            assert "blocs" not in response.json["data"][0]
            return count

        # Compared against an empty bloc, not a smaller one: a prefetch that ignores
        # the mask costs a constant batch query, which a "20 vs 2 cards" comparison
        # would not see. An empty bloc has nothing to load, so it gives the baseline.
        filled, empty = query_count(20), query_count(0)
        assert filled == empty, (
            f"the query count grows with the bloc contents ({filled} with cards, "
            f"{empty} without): the masked-out blocs are dereferenced"
        )

    def test_search_post(self):
        """It should fetch a post list from the API"""
        name_match = PostFactory(name="Foobar", published="2025-01-01")
        content_match = PostFactory(content="Foobar", published="2025-01-02")
        PostFactory(content="Something else")

        response = self.get(url_for("api.posts", q="Foobar"))
        assert200(response)
        assert len(response.json["data"]) == 2

        assert response.json["data"][0]["id"] == str(name_match.id)
        assert response.json["data"][1]["id"] == str(content_match.id)

        response = self.get(url_for("api.posts", q="Foobar", sort="-published"))
        assert200(response)
        assert len(response.json["data"]) == 2

        assert response.json["data"][1]["id"] == str(name_match.id)
        assert response.json["data"][0]["id"] == str(content_match.id)

    def test_post_api_get(self):
        """It should fetch a post from the API"""
        admin = AdminFactory()
        post = PostFactory(owner=admin)
        response = self.get(url_for("api.post", post=post))
        assert200(response)
        owner = response.json["owner"]
        assert isinstance(owner, dict)
        assert owner["id"] == str(admin.id)

    def test_post_api_get_draft(self):
        """An unpublished post should only be readable by a sysadmin"""
        draft = PostFactory(published=None)

        assert404(self.get(url_for("api.post", post=draft)))

        self.login(UserFactory())
        assert404(self.get(url_for("api.post", post=draft)))

        self.login(AdminFactory())
        response = self.get(url_for("api.post", post=draft))
        assert200(response)
        assert response.json["id"] == str(draft.id)

    def test_post_api_get_with_dangling_dataset_reference(self):
        """Getting a post should not crash when one of its datasets was hard-deleted,
        leaving a dangling DBRef that bypassed `reverse_delete_rule=PULL`."""
        kept = DatasetFactory()
        deleted = DatasetFactory()
        post = PostFactory(datasets=[kept, deleted])

        # Hard-delete the dataset bypassing MongoEngine signals (and thus the
        # reverse_delete_rule), so the post keeps a dangling DBRef.
        deleted_id = deleted.id
        DatasetFactory._meta.model._get_collection().delete_one({"_id": deleted_id})

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        dataset_ids = [d["id"] for d in response.json["datasets"]]
        assert dataset_ids == [str(kept.id)]

    def test_post_api_get_with_dangling_dataset_in_bloc(self):
        """Getting a post should not crash when a `DatasetsListBloc` references a
        hard-deleted dataset. Bloc references live in `EmbeddedDocument`s, which
        MongoEngine never cleans through `reverse_delete_rule`, so dangling DBRefs
        are expected there."""
        kept = DatasetFactory()
        deleted = DatasetFactory()
        post = PostFactory(
            body_type="blocs",
            blocs=[DatasetsListBloc(title="Featured", datasets=[kept, deleted])],
        )

        DatasetFactory._meta.model._get_collection().delete_one({"_id": deleted.id})

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        bloc_datasets = response.json["blocs"][0]["datasets"]
        assert [d["id"] for d in bloc_datasets] == [str(kept.id)]

    def test_post_api_get_with_dangling_dataset_in_nested_accordion_bloc(self):
        """Reproduces the production crash: a `DatasetsListBloc` nested inside an
        `AccordionListBloc` references a hard-deleted dataset. `purge_blocs_references`
        does not descend into accordion items, so the dangling DBRef survives the purge."""
        kept = DatasetFactory()
        deleted = DatasetFactory()
        post = PostFactory(
            body_type="blocs",
            blocs=[
                AccordionListBloc(
                    title="Accordion",
                    items=[
                        AccordionItemBloc(
                            title="Item",
                            content=[DatasetsListBloc(title="Featured", datasets=[kept, deleted])],
                        )
                    ],
                )
            ],
        )

        DatasetFactory._meta.model._get_collection().delete_one({"_id": deleted.id})

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        bloc_datasets = response.json["blocs"][0]["items"][0]["content"][0]["datasets"]
        assert [d["id"] for d in bloc_datasets] == [str(kept.id)]

    def test_post_api_create(self):
        """It should create a post from the API"""
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        self.login(AdminFactory())
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert Post.objects.count() == 1
        post = Post.objects.first()
        for dataset, expected in zip(post.datasets, data["datasets"]):
            assert str(dataset.id) == expected
        for reuse, expected in zip(post.reuses, data["reuses"]):
            assert str(reuse.id) == expected

    def test_post_api_update(self):
        """It should update a post from the API"""
        post = PostFactory()
        data = post.to_dict()
        data["content"] = "new content"
        self.login(AdminFactory())
        response = self.put(url_for("api.post", post=post), data)
        assert200(response)
        assert Post.objects.count() == 1
        assert Post.objects.first().content == "new content"

    def test_post_api_update_with_related_dataset_and_reuse(self):
        """It should update a post from the API with related dataset and reuse"""
        self.login(AdminFactory())
        post = PostFactory()
        data = post.to_dict()
        data["content"] = "new content"

        # Add datasets
        data["datasets"] = [DatasetFactory().to_dict()]
        response = self.put(url_for("api.post", post=post), data)
        assert200(response)

        # Add reuses to the post value returned by the previous api call
        data = response.json
        data["reuses"] = [ReuseFactory().to_dict()]
        response = self.put(url_for("api.post", post=post), data)
        assert200(response)

        assert len(response.json["datasets"]) == 1
        assert len(response.json["reuses"]) == 1

    def test_post_api_delete(self):
        """It should delete a post from the API"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.delete(url_for("api.post", post=post))
        assert204(response)
        assert Post.objects.count() == 0

    def test_post_api_publish(self):
        """It should update a post from the API"""
        post = PostFactory(published=None)
        self.login(AdminFactory())
        response = self.post(url_for("api.publish_post", post=post))
        assert200(response)
        assert Post.objects.count() == 1

        post.reload()
        assert post.published is not None

    def test_post_api_unpublish(self):
        """It should update a post from the API"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.delete(url_for("api.publish_post", post=post))
        assert200(response)
        assert Post.objects.count() == 1

        post.reload()
        assert post.published is None

    def test_post_api_create_with_empty_credit_url(self):
        """It should create a post with an empty credit_url (converted to None)"""
        data = PostFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        data["credit_url"] = ""
        self.login(AdminFactory())
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert Post.objects.count() == 1
        post = Post.objects.first()
        assert post.credit_url is None

    def test_post_api_list_with_drafts_non_admin(self):
        """Non-admin users should not see drafts even with with_drafts=True"""
        PostFactory.create_batch(3)
        PostFactory(published=None)

        self.login(UserFactory())
        response = self.get(url_for("api.posts", with_drafts=True))
        assert200(response)
        assert len(response.json["data"]) == 3

    def test_post_search_api_excludes_drafts(self):
        """The v2 search endpoint should never expose unpublished posts"""
        published = PostFactory.create_batch(3)
        PostFactory(published=None)
        expected = {str(post.id) for post in published}

        response = self.get(url_for("apiv2.post_search"))
        assert200(response)
        assert response.json["total"] == 3
        assert {p["id"] for p in response.json["data"]} == expected

        # Unlike the v1 list endpoint, the v2 search has no `with_drafts` bypass:
        # drafts are not indexed at all, so sysadmins do not see them either.
        self.login(AdminFactory())

        response = self.get(url_for("apiv2.post_search"))
        assert200(response)
        assert response.json["total"] == 3
        assert {p["id"] for p in response.json["data"]} == expected

    def test_post_search_api_filters_on_query_and_tags(self):
        """The Mongo fallback of the v2 search should actually apply `q` and `tag`"""
        named = PostFactory(name="Foobar", tags=["transport"])
        both_tags = PostFactory(name="Something else", tags=["transport", "sante"])
        PostFactory(name="Something else", tags=["sante"])

        response = self.get(url_for("apiv2.post_search", q="Foobar"))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(named.id)]

        response = self.get(url_for("apiv2.post_search", tag="transport"))
        assert200(response)
        assert {p["id"] for p in response.json["data"]} == {str(named.id), str(both_tags.id)}

        response = self.get(url_for("apiv2.post_search", tag=["transport", "sante"]))
        assert200(response)
        assert [p["id"] for p in response.json["data"]] == [str(both_tags.id)]

    def test_post_api_create_with_blocs(self):
        """It should create a post with body_type='blocs' and inline blocs"""
        datasets = DatasetFactory.create_batch(2)
        self.login(AdminFactory())
        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [
                {
                    "class": "DatasetsListBloc",
                    "title": "Featured datasets",
                    "datasets": [str(d.id) for d in datasets],
                }
            ],
        }
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        post = Post.objects.first()
        assert post.body_type == "blocs"
        assert len(post.blocs) == 1
        assert post.blocs[0].title == "Featured datasets"

    def test_post_api_get_with_blocs(self):
        """It should return blocs directly on the post"""
        datasets = DatasetFactory.create_batch(2)
        bloc = DatasetsListBloc(title="Featured datasets", datasets=datasets)
        post = PostFactory(body_type="blocs", blocs=[bloc])
        response = self.get(url_for("api.post", post=post))
        assert200(response)
        assert response.json["body_type"] == "blocs"
        assert "blocs" in response.json
        assert len(response.json["blocs"]) == 1
        assert response.json["blocs"][0]["class"] == "DatasetsListBloc"
        assert response.json["blocs"][0]["title"] == "Featured datasets"
        assert len(response.json["blocs"][0]["datasets"]) == 2

    def test_post_api_get_blocs_only_returns_card_fields(self):
        """Blocs should return lightweight card representations, not full nested objects"""
        datasets = DatasetFactory.create_batch(2)
        reuses = ReuseFactory.create_batch(2)
        dataservices = DataserviceFactory.create_batch(2)
        post = PostFactory(
            body_type="blocs",
            blocs=[
                DatasetsListBloc(title="Datasets", datasets=datasets),
                ReusesListBloc(title="Reuses", reuses=reuses),
                DataservicesListBloc(title="Dataservices", dataservices=dataservices),
            ],
        )
        response = self.get(url_for("api.post", post=post))
        assert200(response)

        dataset_json = response.json["blocs"][0]["datasets"][0]
        assert "id" in dataset_json
        assert "title" in dataset_json
        assert "resources" not in dataset_json
        assert "community_resources" not in dataset_json

        reuse_json = response.json["blocs"][1]["reuses"][0]
        assert "id" in reuse_json
        assert "title" in reuse_json
        assert "datasets" not in reuse_json

        dataservice_json = response.json["blocs"][2]["dataservices"][0]
        assert "id" in dataservice_json
        assert "title" in dataservice_json
        assert "datasets" not in dataservice_json

    def test_post_api_filter_by_kind(self):
        """It should filter posts by kind"""
        news_post = PostFactory(kind="news")
        page_post = PostFactory(kind="page")

        response = self.get(url_for("api.posts", kind="news"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(news_post.id)

        response = self.get(url_for("api.posts", kind="page"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(page_post.id)

    def test_rss_feed_only_returns_news(self):
        """RSS feed should only return posts with kind=news"""
        news_post = PostFactory(kind="news")
        page_post = PostFactory(kind="page")

        response = self.get(url_for("api.recent_posts_atom_feed"))
        assert200(response)
        content = response.data.decode("utf-8")
        assert news_post.name in content
        assert page_post.name not in content

    def test_post_image_upload(self):
        """An admin should upload a post image into the images storage"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.post(
            url_for("api.post_image", post=post),
            {"file": (create_test_image(), "test.png")},
            json=False,
        )
        assert200(response)
        assert response.json["success"]

        post.reload()
        assert post.image
        assert post.image.filename in storages.images
        assert post.image.original in storages.images

    def test_post_image_upload_requires_admin(self):
        """It should forbid a non-admin from uploading a post image"""
        post = PostFactory()
        self.login(UserFactory())
        response = self.post(
            url_for("api.post_image", post=post),
            {"file": (create_test_image(), "test.png")},
            json=False,
        )
        assert403(response)

    def test_post_image_upload_rejects_non_image(self):
        """It should reject a non-image file"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.post(
            url_for("api.post_image", post=post),
            {"file": (BytesIO(b"not an image"), "payload.txt")},
            json=False,
        )
        assert400(response)
