from flask import url_for

from udata.core.linkable import Linkable
from udata.core.storages import default_image_basename, images
from udata.i18n import lazy_gettext as _
from udata.mongo import db
from udata.uris import cdata_url

from .constants import BODY_TYPES, IMAGE_SIZES

__all__ = ("Post",)


class PostQuerySet(db.BaseQuerySet):
    def published(self):
        return self(published__ne=None).order_by("-published")


class Post(db.Datetimed, Linkable, db.Document):
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from="name", update=True, follow=True
    )
    headline = db.StringField()
    content = db.StringField(required=True)
    image_url = db.StringField()
    image = db.ImageField(fs=images, basename=default_image_basename, thumbnails=IMAGE_SIZES)

    credit_to = db.StringField()
    credit_url = db.URLField()

    tags = db.ListField(db.StringField())
    datasets = db.ListField(db.ReferenceField("Dataset", reverse_delete_rule=db.PULL))
    reuses = db.ListField(db.ReferenceField("Reuse", reverse_delete_rule=db.PULL))

    owner = db.ReferenceField("User")
    published = db.DateTimeField()

    body_type = db.StringField(choices=list(BODY_TYPES), default="markdown", required=False)

    meta = {
        "ordering": ["-created_at"],
        "indexes": [
            "-created_at",
            "-published",
            {
                "fields": ["$name", "$headline", "$content"],
                "default_language": "french",
                "weights": {"name": 10, "headline": 5, "content": 4},
            },
        ],
        "queryset_class": PostQuerySet,
    }

    verbose_name = _("post")

    def __str__(self):
        return self.name or ""

    def self_web_url(self, **kwargs):
        return cdata_url(f"/posts/{self._link_id(**kwargs)}/", **kwargs)

    def self_api_url(self, **kwargs):
        return url_for(
            "api.post", post=self._link_id(**kwargs), **self._self_api_url_kwargs(**kwargs)
        )

    def count_discussions(self):
        # There are no metrics on Post to store discussions count
        pass
