from io import BytesIO
from unittest import mock
from uuid import uuid4

import pytest
from flask import url_for
from mongoengine.context_managers import query_counter
from PIL import Image

from udata.core import storages
from udata.core.access_type.constants import AccessAudienceCondition, AccessAudienceType
from udata.core.access_type.models import AccessAudience
from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.discussions.models import Discussion
from udata.core.edito_blocs.models import (
    AccordionItemBloc,
    AccordionListBloc,
    ColumnBloc,
    DataserviceBloc,
    DatasetBloc,
    ExploreBloc,
    ReuseBloc,
    SectionBloc,
    TitleBloc,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.features.notifications.settings import NotificationSetting
from udata.tests.api import APITestCase, PytestOnlyAPITestCase
from udata.tests.helpers import (
    assert200,
    assert201,
    assert204,
    assert400,
    assert403,
    assert404,
    create_test_image,
)


def side_by_side(blocs, width="1/2"):
    for bloc in blocs:
        bloc.width = width
    return blocs


def object_cards(value):
    """The serialized datasets/reuses/dataservices shown anywhere in a blocs tree."""
    if isinstance(value, list):
        for item in value:
            yield from object_cards(item)
    elif isinstance(value, dict):
        for key in ("dataset", "reuse", "dataservice"):
            if value.get("class", "").lower() == f"{key}bloc":
                yield value[key]
        for item in value.values():
            yield from object_cards(item)


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
        bloc = SectionBloc(blocs=[TitleBloc(title="Test")])
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

            # Datasets spread across 4 sections + 2 accordion items, one bloc per dataset.
            sections = [
                SectionBloc(blocs=side_by_side([DatasetBloc(dataset=d) for d in datasets()]))
                for _ in range(4)
            ]
            accordion = AccordionListBloc(
                items=[
                    AccordionItemBloc(
                        title=f"Item {i}",
                        content=side_by_side([DatasetBloc(dataset=d) for d in datasets()]),
                    )
                    for i in range(2)
                ],
            )
            reuses = [ReuseFactory(organization=orgs[i % len(orgs)]) for i in range(cards_per_bloc)]
            dataservices = [
                DataserviceFactory(organization=orgs[i % len(orgs)]) for i in range(cards_per_bloc)
            ]
            blocs = sections + [
                SectionBloc(
                    blocs=[
                        accordion,
                        *side_by_side([ReuseBloc(reuse=r) for r in reuses], width="1/3"),
                        *side_by_side([DataserviceBloc(dataservice=d) for d in dataservices]),
                    ]
                )
            ]
            post = PostFactory(body_type="blocs", content=None, blocs=blocs, datasets=[], reuses=[])

            url = url_for("api.post", post=post)
            assert200(self.get(url))  # warm up one-time queries

            with query_counter() as counter:
                response = self.get(url)
                count = int(counter)
            assert200(response)

            # A reference the prefetch fails to resolve silently drops its bloc — which
            # *lowers* the query count. Assert every card is there, with its
            # organization resolved, so a flat count really means "batched".
            org_ids = {str(o.id) for o in orgs}
            cards = list(object_cards(response.json["blocs"]))
            # 6 rows of datasets (4 in sections, 2 in the accordion), reuses, dataservices
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
                SectionBloc(
                    blocs=[
                        *side_by_side([DatasetBloc(dataset=d) for d in datasets]),
                        *side_by_side([ReuseBloc(reuse=r) for r in reuses], width="1/3"),
                        *side_by_side([DataserviceBloc(dataservice=d) for d in dataservices]),
                    ]
                )
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
        card = next(object_cards(projected["blocs"]))
        assert card["quality"]["has_resources"] is True

    def test_post_api_blocs_preserve_reference_order(self):
        """Batch-loading the referenced objects must not swap them between blocs.

        `id__in` returns the documents in the model's default order (`Dataset` sorts
        by `-created_at_internal`), not in the order of the blocs, so the prefetch
        assigns each document back to the bloc referencing it. Blocs are editorial
        content: their order is the behaviour.
        """
        created = [DatasetFactory() for _ in range(6)]
        # Interleaved, so the bloc order matches neither the creation order nor its
        # reverse — the two orders a batch query can return on its own.
        datasets = created[::2] + created[1::2]
        post = PostFactory(
            body_type="blocs",
            content=None,
            blocs=[SectionBloc(blocs=side_by_side([DatasetBloc(dataset=d) for d in datasets]))],
            datasets=[],
            reuses=[],
        )

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        cards = list(object_cards(response.json["blocs"]))
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
            datasets = [DatasetFactory(organization=org) for _ in range(nb_cards)]
            post.blocs = (
                [SectionBloc(blocs=[DatasetBloc(dataset=d) for d in datasets])] if datasets else []
            )
            post.save()

            url = url_for("api.posts")
            assert200(self.get(url))  # warm up one-time queries

            with query_counter() as counter:
                response = self.get(url)
                count = int(counter)
            assert200(response)
            assert "blocs" not in response.json["data"][0]
            return count

        # Compared against no blocs, not fewer cards: a prefetch that ignores the mask
        # costs a constant batch query, which a "20 vs 2 cards" comparison would not see.
        # Without blocs, there is nothing to load, so it gives the baseline.
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

    def make_post_with_dangling_dataset_blocs(self):
        """A post showing a dataset that is then hard-deleted, in a section and in an
        accordion. Bloc references live in `EmbeddedDocument`s, which MongoEngine never
        cleans through `reverse_delete_rule`, so dangling references are expected there.
        """
        kept = DatasetFactory()
        deleted = DatasetFactory()
        nested = AccordionListBloc(
            items=[AccordionItemBloc(title="Item", content=[DatasetBloc(dataset=deleted)])]
        )
        post = PostFactory(
            body_type="blocs",
            blocs=[
                SectionBloc(
                    blocs=side_by_side([DatasetBloc(dataset=kept), DatasetBloc(dataset=deleted)])
                ),
                SectionBloc(blocs=[nested]),
            ],
        )
        DatasetFactory._meta.model._get_collection().delete_one({"_id": deleted.id})
        return post, kept

    def test_post_api_get_with_dangling_dataset_in_bloc(self):
        """A bloc showing a hard-deleted dataset is left out, wherever it is, with the
        containers it leaves empty: everything up to the second section."""
        post, kept = self.make_post_with_dangling_dataset_blocs()

        response = self.get(url_for("api.post", post=post))
        assert200(response)
        (section,) = response.json["blocs"]
        assert [bloc["dataset"]["id"] for bloc in section["blocs"]] == [str(kept.id)]

    def test_post_api_blocs_with_dangling_dataset_can_be_saved_back(self):
        """The editor sends back the blocs it read: a dangling reference must not make the
        page impossible to save."""
        post, kept = self.make_post_with_dangling_dataset_blocs()
        self.login(AdminFactory())

        blocs = self.get(url_for("api.post", post=post)).json["blocs"]
        response = self.put(url_for("api.post", post=post), {"blocs": blocs})

        assert200(response)
        post.reload()
        (section,) = post.blocs
        assert [(bloc.dataset.id, bloc.width) for bloc in section.blocs] == [(kept.id, "1/2")]

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

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr")
    def test_post_api_create_page_with_parent(self):
        """A sub-page exposes its ancestors, and lives under /pages/<path>"""
        elections = PostFactory(kind="page", name="Élections", slug="elections")
        municipales = PostFactory(
            kind="page", name="Municipales", slug="municipales", parent=elections
        )
        self.login(AdminFactory())

        response = self.post(
            url_for("api.posts"),
            {"name": "2026", "content": "x", "kind": "page", "parent": str(municipales.id)},
        )
        assert201(response)
        assert response.json["page"] == "https://www.data.gouv.fr/pages/elections/municipales/2026"
        assert response.json["parent"] == {
            "id": str(municipales.id),
            "name": "Municipales",
            "page": "https://www.data.gouv.fr/pages/elections/municipales",
        }
        assert [ancestor["page"] for ancestor in response.json["ancestors"]] == [
            "https://www.data.gouv.fr/pages/elections",
            "https://www.data.gouv.fr/pages/elections/municipales",
        ]

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr")
    def test_post_api_news_page_url(self):
        """A news stays under /posts/<slug>, a root page goes under /pages/<slug>"""
        news = PostFactory(kind="news", slug="actualite")
        page = PostFactory(kind="page", slug="cgu")

        assert self.get(url_for("api.post", post=news)).json["page"] == (
            "https://www.data.gouv.fr/posts/actualite"
        )
        response = self.get(url_for("api.post", post=page)).json
        assert response["page"] == "https://www.data.gouv.fr/pages/cgu"
        assert response["parent"] is None
        assert response["ancestors"] == []

    def test_post_api_parent_must_be_a_page(self):
        """Only a page can have a parent, and that parent must be a page"""
        news = PostFactory(kind="news")
        page = PostFactory(kind="page")
        self.login(AdminFactory())

        response = self.post(
            url_for("api.posts"),
            {"name": "Sous-page", "content": "x", "kind": "page", "parent": str(news.id)},
        )
        assert400(response)
        response = self.post(
            url_for("api.posts"),
            {"name": "Actualité", "content": "x", "kind": "news", "parent": str(page.id)},
        )
        assert400(response)
        assert Post.objects.count() == 2

    def test_post_api_parent_cannot_create_a_cycle(self):
        """A page cannot be moved under one of its own descendants, nor under itself"""
        root = PostFactory(kind="page")
        child = PostFactory(kind="page", parent=root)
        grandchild = PostFactory(kind="page", parent=child)
        self.login(AdminFactory())

        assert400(self.put(url_for("api.post", post=root), {"parent": str(child.id)}))
        assert400(self.put(url_for("api.post", post=root), {"parent": str(grandchild.id)}))
        assert400(self.put(url_for("api.post", post=root), {"parent": str(root.id)}))
        root.reload()
        assert root.parent is None

    def test_post_api_get_page_in_a_cycle(self):
        """A cycle written behind `clean()` (two concurrent moves) must not hang the reads"""
        first = PostFactory(kind="page", slug="first")
        second = PostFactory(kind="page", slug="second", parent=first)
        Post.objects(id=first.id).update_one(set__parent=second)

        assert200(self.get(url_for("api.post", post=second)))

    def test_post_api_published_page_cannot_be_under_a_draft(self):
        """A published sub-page would expose the name and slug of its draft parent"""
        draft = PostFactory(kind="page", published=None)
        child = PostFactory(kind="page", published=None, parent=draft)
        self.login(AdminFactory())

        assert400(self.post(url_for("api.publish_post", post=child)))
        child.reload()
        assert child.published is None

        published = PostFactory(kind="page")
        assert400(self.put(url_for("api.post", post=published), {"parent": str(draft.id)}))
        published.reload()
        assert published.parent is None

    def test_post_api_unpublish_page_with_published_children(self):
        """Unpublishing a parent would turn it into a draft exposed by its sub-pages"""
        parent = PostFactory(kind="page")
        PostFactory(kind="page", parent=parent)
        self.login(AdminFactory())

        assert400(self.delete(url_for("api.publish_post", post=parent)))
        parent.reload()
        assert parent.published is not None

    def test_post_api_unpublish_page_with_draft_children(self):
        """Draft sub-pages expose nothing: their parent can still be unpublished"""
        parent = PostFactory(kind="page")
        PostFactory(kind="page", published=None, parent=parent)
        self.login(AdminFactory())

        assert200(self.delete(url_for("api.publish_post", post=parent)))
        parent.reload()
        assert parent.published is None

    def test_post_api_page_with_children_must_stay_a_page(self):
        """Turning a page with sub-pages into a news would leave them under a news"""
        root = PostFactory(kind="page")
        PostFactory(kind="page", parent=root)
        self.login(AdminFactory())

        assert400(self.put(url_for("api.post", post=root), {"kind": "news"}))
        root.reload()
        assert root.kind == "page"

    @pytest.mark.options(CDATA_BASE_URL="https://www.data.gouv.fr")
    def test_post_api_move_page_to_root(self):
        """Removing the parent moves the page back to the root"""
        root = PostFactory(kind="page", slug="elections")
        child = PostFactory(kind="page", slug="municipales", parent=root)
        self.login(AdminFactory())

        response = self.put(url_for("api.post", post=child), {"parent": None})
        assert200(response)
        assert response.json["page"] == "https://www.data.gouv.fr/pages/municipales"
        child.reload()
        assert child.parent is None

    def test_post_api_resend_parent_as_object(self):
        """A client resending the parent as it reads it must keep it unchanged"""
        root = PostFactory(kind="page")
        child = PostFactory(kind="page", parent=root)
        self.login(AdminFactory())
        data = self.get(url_for("api.post", post=child)).json

        response = self.put(url_for("api.post", post=child), {"parent": data["parent"]})
        assert200(response)
        assert response.json["parent"]["id"] == str(root.id)

    def test_post_api_delete_page_with_children(self):
        """A page with sub-pages cannot be deleted, and nothing of it is deleted"""
        root = PostFactory(kind="page")
        PostFactory(kind="page", parent=root)
        DiscussionFactory(subject=root)
        self.login(AdminFactory())

        assert400(self.delete(url_for("api.post", post=root)))
        assert Post.objects(id=root.id).count() == 1
        assert Discussion.objects(subject=root).count() == 1

    def test_post_api_create_with_slug(self):
        """A sysadmin should choose the slug instead of deriving it from the name"""
        self.login(AdminFactory())
        data = {"name": "Conditions générales d'utilisation", "content": "CGU", "slug": "cgu"}

        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert response.json["slug"] == "cgu"
        assert Post.objects.get().slug == "cgu"

    def test_post_api_create_with_taken_slug(self):
        """A chosen slug already used by another post is rejected, not silently suffixed"""
        PostFactory(slug="cgu")
        self.login(AdminFactory())
        data = {"name": "Conditions générales d'utilisation", "content": "CGU", "slug": "CGU"}

        response = self.post(url_for("api.posts"), data)
        assert400(response)
        assert "slug" in response.json["errors"]
        assert Post.objects.count() == 1

    def test_post_api_update_with_taken_slug(self):
        """Taking the slug of another post on update is rejected"""
        PostFactory(slug="cgu")
        post = PostFactory(slug="mentions-legales")
        self.login(AdminFactory())

        assert400(self.put(url_for("api.post", post=post), {"slug": "cgu"}))
        post.reload()
        assert post.slug == "mentions-legales"

    def test_post_api_update_with_own_slug(self):
        """Resending the post's own slug, even unnormalized, is not a conflict"""
        post = PostFactory(slug="cgu")
        self.login(AdminFactory())

        response = self.put(url_for("api.post", post=post), {"slug": "CGU", "content": "new"})
        assert200(response)
        assert response.json["slug"] == "cgu"

    def test_post_api_create_with_slug_derived_from_taken_name(self):
        """A slug derived from the name still gets a uniqueness suffix"""
        PostFactory(slug="cgu")
        self.login(AdminFactory())

        response = self.post(url_for("api.posts"), {"name": "CGU", "content": "CGU"})
        assert201(response)
        assert response.json["slug"] == "cgu-1"

    def test_post_api_update_slug(self):
        """Changing the slug keeps the old one redirecting to the post"""
        post = PostFactory(name="Conditions générales d'utilisation")
        old_slug = post.slug
        self.login(AdminFactory())

        response = self.put(url_for("api.post", post=post), {"slug": "Mes CGU"})
        assert200(response)
        assert response.json["slug"] == "mes-cgu"

        response = self.get(url_for("api.post", post=old_slug))
        assert response.status_code == 308
        assert response.location.endswith(url_for("api.post", post="mes-cgu"))

    def test_post_api_create_with_empty_slug(self):
        """An empty slug falls back to the one derived from the name"""
        self.login(AdminFactory())
        data = {"name": "Conditions générales d'utilisation", "content": "CGU", "slug": ""}

        response = self.post(url_for("api.posts"), data)
        assert201(response)
        assert response.json["slug"] == "conditions-generales-dutilisation"

    def test_post_api_update_with_empty_slug(self):
        """Clearing the slug on update is rejected, instead of saving a post without slug"""
        post = PostFactory(name="faq", slug="faq")
        self.login(AdminFactory())

        assert400(self.put(url_for("api.post", post=post), {"slug": ""}))
        post.reload()
        assert post.slug == "faq"

    def test_post_api_create_with_slug_without_letters_or_digits(self):
        """A slug that normalizes to nothing is rejected, instead of saving an empty slug"""
        self.login(AdminFactory())
        data = {"name": "Conditions générales d'utilisation", "content": "CGU", "slug": "!!!"}

        response = self.post(url_for("api.posts"), data)
        assert400(response)
        assert "slug" in response.json["errors"]
        assert Post.objects.count() == 0

    def test_post_api_slug_must_be_a_string(self):
        """A slug that is not a string is rejected, at creation as on update"""
        post = PostFactory(slug="cgu")
        self.login(AdminFactory())

        for slug in (123, True, ["cgu"]):
            response = self.post(
                url_for("api.posts"), {"name": "CGU", "content": "x", "slug": slug}
            )
            assert400(response)
            assert400(self.put(url_for("api.post", post=post), {"slug": slug}))
        assert Post.objects.count() == 1
        post.reload()
        assert post.slug == "cgu"

    def test_post_api_reclaim_the_previous_slug_of_another_post(self):
        """A previous slug can be given to a new post (a new version of /cgu): it then
        serves this post instead of redirecting to the old one"""
        old = PostFactory(name="CGU 2025", slug="cgu")
        self.login(AdminFactory())
        assert200(self.put(url_for("api.post", post=old), {"slug": "cgu-2025"}))

        response = self.post(url_for("api.posts"), {"name": "CGU", "content": "x", "slug": "cgu"})
        assert201(response)
        new_id = response.json["id"]

        response = self.get(url_for("api.post", post="cgu"))
        assert200(response)
        assert response.json["id"] == new_id

    def test_post_api_rename_keeps_the_slug(self):
        """Renaming a post keeps its URL, whether the slug is resent as-is or left out"""
        post = PostFactory(name="CGU", slug="cgu")
        self.login(AdminFactory())

        response = self.put(
            url_for("api.post", post=post), {"name": "Conditions générales", "slug": "cgu"}
        )
        assert200(response)
        assert response.json["slug"] == "cgu"

        response = self.put(url_for("api.post", post=post), {"name": "Conditions d'utilisation"})
        assert200(response)
        assert response.json["slug"] == "cgu"

    def test_post_api_update_slug_requires_admin(self):
        """A non-sysadmin cannot change a post slug"""
        post = PostFactory()
        slug = post.slug
        self.login(UserFactory())

        assert403(self.put(url_for("api.post", post=post), {"slug": "cgu"}))
        post.reload()
        assert post.slug == slug

    def test_post_api_delete(self):
        """It should delete a post from the API"""
        post = PostFactory()
        self.login(AdminFactory())
        response = self.delete(url_for("api.post", post=post))
        assert204(response)
        assert Post.objects.count() == 0

    def test_deleting_a_post_deletes_its_discussions_and_the_rules_on_them(self):
        """Left behind, a thread about nothing breaks the list of rules of whoever
        followed it."""
        post = PostFactory()
        discussion = DiscussionFactory(subject=post)
        follower = UserFactory()
        NotificationSetting.objects.create(
            user=follower, scope=discussion, event="discussion", enabled=True
        )
        self.login(AdminFactory())

        assert204(self.delete(url_for("api.post", post=post)))

        assert Discussion.objects.count() == 0
        assert NotificationSetting.objects.count() == 0
        self.login(follower)
        assert200(self.get(url_for("api.notification_settings")))

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
        resource_id = DatasetFactory(visible=True).resources[0].id
        self.login(AdminFactory())
        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [
                {
                    "class": "SectionBloc",
                    "color": "purple",
                    "blocs": [
                        {"class": "TitleBloc", "title": "Hero"},
                        {"class": "ButtonBloc", "title": "Go", "url": "https://example.com"},
                    ],
                },
                {
                    "class": "SectionBloc",
                    "blocs": [
                        {"class": "TitleBloc", "title": "Featured datasets", "subtitle": "Sub"},
                        *(
                            {"class": "DatasetBloc", "width": "1/3", "dataset": str(d.id)}
                            for d in datasets
                        ),
                        {"class": "ExploreBloc", "resource_id": str(resource_id)},
                    ],
                },
            ],
        }
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        post = Post.objects.first()
        assert post.body_type == "blocs"
        hero, section = post.blocs
        assert hero.color == "purple"
        hero_title, button = hero.blocs
        assert hero_title.title == "Hero"
        assert (button.title, button.url) == ("Go", "https://example.com")
        assert section.color is None
        title, *objects, explore = section.blocs
        assert (title.title, title.subtitle) == ("Featured datasets", "Sub")
        assert [bloc.width for bloc in objects] == ["1/3", "1/3"]
        assert [bloc.dataset.id for bloc in objects] == [d.id for d in datasets]
        assert isinstance(explore, ExploreBloc)
        assert explore.resource_id == resource_id

    def test_post_api_bloc_width_is_optional(self):
        """A bloc without a width takes the whole row."""
        self.login(AdminFactory())
        data = {
            "name": "Widths",
            "body_type": "blocs",
            "blocs": [
                {
                    "class": "SectionBloc",
                    "blocs": [
                        {"class": "TitleBloc", "title": "A", "width": "2/3"},
                        {"class": "TitleBloc", "title": "B"},
                    ],
                }
            ],
        }
        response = self.post(url_for("api.posts"), data)
        assert201(response)
        blocs = response.json["blocs"][0]["blocs"]
        assert [bloc["width"] for bloc in blocs] == ["2/3", None]

    def test_post_api_create_with_explore_bloc_unknown_resource(self):
        """An ExploreBloc must point to an existing resource"""
        self.login(AdminFactory())
        for resource_id in (str(uuid4()), "not-a-uuid"):
            data = {
                "name": "Test explore post",
                "body_type": "blocs",
                "blocs": [
                    {
                        "class": "SectionBloc",
                        "blocs": [{"class": "ExploreBloc", "resource_id": resource_id}],
                    }
                ],
            }
            response = self.post(url_for("api.posts"), data)
            assert400(response)
        assert Post.objects.count() == 0

    def test_post_api_get_with_blocs(self):
        """It should return blocs directly on the post"""
        dataset = DatasetFactory()
        post = PostFactory(
            body_type="blocs",
            blocs=[
                SectionBloc(
                    blocs=[TitleBloc(title="Featured"), DatasetBloc(dataset=dataset, width="1/2")]
                )
            ],
        )
        response = self.get(url_for("api.post", post=post))
        assert200(response)
        assert response.json["body_type"] == "blocs"
        section = response.json["blocs"][0]
        assert section["class"] == "SectionBloc"
        title, dataset_bloc = section["blocs"]
        assert (title["class"], title["title"]) == ("TitleBloc", "Featured")
        assert (dataset_bloc["class"], dataset_bloc["width"]) == ("DatasetBloc", "1/2")
        assert dataset_bloc["dataset"]["id"] == str(dataset.id)

    def test_post_api_get_blocs_only_returns_card_fields(self):
        """Blocs should return lightweight card representations, not full nested objects"""
        post = PostFactory(
            body_type="blocs",
            blocs=[
                SectionBloc(
                    blocs=[
                        DatasetBloc(dataset=DatasetFactory()),
                        ReuseBloc(reuse=ReuseFactory()),
                        DataserviceBloc(dataservice=DataserviceFactory()),
                    ]
                )
            ],
        )
        response = self.get(url_for("api.post", post=post))
        assert200(response)

        dataset_json, reuse_json, dataservice_json = object_cards(response.json["blocs"])
        assert "id" in dataset_json
        assert "title" in dataset_json
        assert "resources" not in dataset_json
        assert "community_resources" not in dataset_json

        assert "id" in reuse_json
        assert "title" in reuse_json
        assert "datasets" not in reuse_json

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

    def test_post_image_upload_of_a_jpeg_holding_several_pictures(self):
        """As phone cameras write them: Pillow reads them as MPO."""
        post = PostFactory()
        self.login(AdminFactory())
        photo = BytesIO()
        frames = [Image.new("RGB", (2, 2), color) for color in ("red", "blue")]
        frames[0].save(photo, "MPO", save_all=True, append_images=frames[1:])
        photo.seek(0)

        response = self.post(
            url_for("api.post_image", post=post), {"file": (photo, "photo.jpg")}, json=False
        )

        assert200(response)
        post.reload()
        assert post.image.filename in storages.images

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


def section(*blocs, **fields):
    return {"class": "SectionBloc", "blocs": list(blocs), **fields}


def accordion(*content):
    return {"class": "AccordionListBloc", "items": [{"title": "I", "content": list(content)}]}


def column(*blocs, **fields):
    return {"class": "ColumnBloc", "blocs": list(blocs), **fields}


TITLE = {"class": "TitleBloc", "title": "T"}


class PostBlocsLayoutAPITest(PytestOnlyAPITestCase):
    # Each case with the reason it is rejected for, so that none passes for another one.
    @pytest.mark.parametrize(
        "blocs,reason",
        [
            pytest.param([TITLE], "TitleBloc is not allowed here", id="leaf-at-top-level"),
            pytest.param(
                [section(section(TITLE))],
                "SectionBloc is not allowed here",
                id="section-in-section",
            ),
            pytest.param([section()], "SectionBloc cannot be empty", id="empty-section"),
            pytest.param([section(TITLE, color="red")], "color", id="unknown-color"),
            pytest.param(
                [section({"class": "ButtonBloc", "title": "B"})], "url", id="button-without-url"
            ),
            # The whole row is stored as no width at all
            pytest.param([section({**TITLE, "width": "1"})], "width", id="whole-row-width"),
            pytest.param([section({**TITLE, "width": "1/5"})], "width", id="unknown-width"),
            pytest.param(
                [section(accordion(accordion()))],
                "AccordionListBloc is not allowed here",
                id="accordion-in-accordion",
            ),
            pytest.param(
                [column(TITLE)], "ColumnBloc is not allowed here", id="column-at-top-level"
            ),
            pytest.param([section(column())], "ColumnBloc cannot be empty", id="empty-column"),
            pytest.param(
                [section(column(column(TITLE)))],
                "ColumnBloc is not allowed here",
                id="column-in-column",
            ),
            pytest.param(
                [section(column(accordion(TITLE)))],
                "AccordionListBloc is not allowed here",
                id="accordion-in-column",
            ),
            pytest.param(
                [section(accordion(column()))],
                "ColumnBloc cannot be empty",
                id="empty-column-in-accordion",
            ),
            pytest.param([section(column(TITLE, width="1/5"))], "width", id="unknown-column-width"),
        ],
    )
    def test_post_api_rejects_blocs_out_of_layout(self, blocs, reason):
        self.login(AdminFactory())
        data = {"name": "Test blocs post", "body_type": "blocs", "blocs": blocs}
        response = self.post(url_for("api.posts"), data)
        assert response.status_code == 400
        assert reason in response.get_data(as_text=True)
        assert Post.objects.count() == 0

    @pytest.mark.parametrize("container", [accordion, column], ids=["accordion", "column"])
    def test_post_api_rejects_the_explorer_in_an_accordion_or_a_column(self, container):
        """The explorer is too wide for an accordion or a column, a share of a row, even of an
        existing resource."""
        dataset = DatasetFactory(resources=[ResourceFactory()])
        explorer = {"class": "ExploreBloc", "resource_id": str(dataset.resources[0].id)}
        self.login(AdminFactory())

        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [section(container(explorer))],
        }
        response = self.post(url_for("api.posts"), data)

        assert response.status_code == 400
        assert "ExploreBloc is not allowed here" in response.get_data(as_text=True)
        # The same explorer is accepted in a section
        data["blocs"] = [section(explorer)]
        assert self.post(url_for("api.posts"), data).status_code == 201

    def test_post_api_accepts_blocs_in_an_accordion(self):
        """The layout the editor and the migration produce: objects side by side, under a
        title, in an accordion item."""
        dataset = DatasetFactory()
        self.login(AdminFactory())
        accordion = {
            "class": "AccordionListBloc",
            "items": [
                {
                    "title": "Item",
                    "content": [
                        {"class": "TitleBloc", "title": "T"},
                        {"class": "DatasetBloc", "width": "1/2", "dataset": str(dataset.id)},
                    ],
                }
            ],
        }
        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [{"class": "SectionBloc", "blocs": [accordion]}],
        }

        response = self.post(url_for("api.posts"), data)

        assert response.status_code == 201
        # Items get an id, which the editor tells them apart by
        assert response.json["blocs"][0]["blocs"][0]["items"][0]["id"]
        title, dataset_bloc = Post.objects.get().blocs[0].blocs[0].items[0].content
        assert title.title == "T"
        assert (dataset_bloc.dataset.id, dataset_bloc.width) == (dataset.id, "1/2")

    def test_post_api_accepts_columns(self):
        """A banner: a title and its text stacked in a column beside an illustration, in a
        section and in an accordion item."""
        self.login(AdminFactory())
        text = {"class": "MarkdownBloc", "content": "Texte"}
        image = {"class": "ImageBloc", "width": "1/4", "image": "https://e.com/i.svg", "alt": None}
        banner = [column(TITLE, text, width="3/4"), image]
        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [section(*banner), section(accordion(*banner))],
        }

        response = self.post(url_for("api.posts"), data)

        assert response.status_code == 201
        served_section, served_accordion_section = response.json["blocs"]
        stored_section, stored_accordion_section = Post.objects.get().blocs
        for served, stored in [
            (served_section["blocs"], stored_section.blocs),
            (
                served_accordion_section["blocs"][0]["items"][0]["content"],
                stored_accordion_section.blocs[0].items[0].content,
            ),
        ]:
            assert [(bloc["class"], bloc["width"]) for bloc in served] == [
                ("ColumnBloc", "3/4"),
                ("ImageBloc", "1/4"),
            ]
            assert [bloc["class"] for bloc in served[0]["blocs"]] == ["TitleBloc", "MarkdownBloc"]
            assert stored[0].blocs[0].title == "T"
            assert stored[0].blocs[1].content == "Texte"

    def test_post_api_accepts_images_and_cards(self):
        """A hero with its illustration, and a summary page linking its subpages with cards,
        down to an accordion item."""
        self.login(AdminFactory())
        image = {"class": "ImageBloc", "width": "1/3", "image": "https://e.com/i.svg", "alt": None}
        card = {
            "class": "CardBloc",
            "width": "1/4",
            "title": "Culture",
            "url": "/pages/donnees_culture",
            "description": "Données sur l'offre culturelle",
            "image": "https://e.com/culture.svg",
        }
        data = {
            "name": "Test blocs post",
            "body_type": "blocs",
            "blocs": [
                section({**TITLE, "width": "2/3"}, image, color="primary"),
                section(card, accordion(card)),
            ],
        }

        response = self.post(url_for("api.posts"), data)

        assert response.status_code == 201
        hero, summary = response.json["blocs"]
        assert {k: hero["blocs"][1][k] for k in image} == image
        assert {k: summary["blocs"][0][k] for k in card} == card
        assert {k: summary["blocs"][1]["items"][0]["content"][0][k] for k in card} == card

    @pytest.mark.parametrize(
        "bloc,field",
        [
            pytest.param({"class": "ImageBloc"}, "image", id="image-without-image"),
            pytest.param({"class": "CardBloc", "url": "/"}, "title", id="card-without-title"),
            pytest.param({"class": "CardBloc", "title": "T"}, "url", id="card-without-url"),
        ],
    )
    def test_post_api_rejects_images_and_cards_without_their_content(self, bloc, field):
        self.login(AdminFactory())
        data = {"name": "Test blocs post", "body_type": "blocs", "blocs": [section(bloc)]}

        response = self.post(url_for("api.posts"), data)

        assert response.status_code == 400
        assert field in response.get_data(as_text=True)
        assert Post.objects.count() == 0


class PostBlocsDeletedObjectsAPITest(PytestOnlyAPITestCase):
    @pytest.mark.parametrize(
        "factory,bloc_cls,ref",
        [
            (DatasetFactory, DatasetBloc, "dataset"),
            (ReuseFactory, ReuseBloc, "reuse"),
            (DataserviceFactory, DataserviceBloc, "dataservice"),
        ],
    )
    def test_blocs_of_hard_deleted_objects_are_left_out(self, factory, bloc_cls, ref):
        """Nothing purges the blocs of a hard-deleted object: they are left out at read, in a
        section, an accordion item and a column, with the containers they leave empty."""
        kept, deleted = factory(), factory()
        post = PostFactory(
            body_type="blocs",
            blocs=[
                SectionBloc(blocs=[bloc_cls(**{ref: deleted}), bloc_cls(**{ref: kept})]),
                SectionBloc(
                    blocs=[
                        AccordionListBloc(
                            items=[
                                AccordionItemBloc(
                                    title="Gone", content=[bloc_cls(**{ref: deleted})]
                                ),
                                AccordionItemBloc(title="Kept", content=[bloc_cls(**{ref: kept})]),
                            ]
                        )
                    ]
                ),
                SectionBloc(
                    blocs=[
                        ColumnBloc(blocs=[bloc_cls(**{ref: deleted})]),
                        ColumnBloc(blocs=[bloc_cls(**{ref: deleted}), bloc_cls(**{ref: kept})]),
                    ]
                ),
            ],
        )
        type(deleted)._get_collection().delete_one({"_id": deleted.id})

        response = self.get(url_for("api.post", post=post))

        assert200(response)
        section, accordion_section, column_section = response.json["blocs"]
        assert [bloc[ref]["id"] for bloc in section["blocs"]] == [str(kept.id)]
        (accordion,) = accordion_section["blocs"]
        assert [item["title"] for item in accordion["items"]] == ["Kept"]
        (kept_column,) = column_section["blocs"]
        assert [bloc[ref]["id"] for bloc in kept_column["blocs"]] == [str(kept.id)]
