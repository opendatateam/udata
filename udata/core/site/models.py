# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g, current_app
from werkzeug.local import LocalProxy

from udata.models import db, WithMetrics
from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse


__all__ = ('Site', 'SiteSettings')


DEFAULT_FEED_SIZE = 20


class SiteSettings(db.EmbeddedDocument):
    home_datasets = db.ListField(db.ReferenceField(Dataset))
    home_reuses = db.ListField(db.ReferenceField(Reuse))


class Site(WithMetrics, db.Document):
    id = db.StringField(primary_key=True)
    title = db.StringField(required=True)
    keywords = db.ListField(db.StringField())
    feed_size = db.IntField(required=True, default=DEFAULT_FEED_SIZE)
    configs = db.DictField()
    themes = db.DictField()
    settings = db.EmbeddedDocumentField(SiteSettings, default=SiteSettings)

    def __unicode__(self):
        return self.title or ''


def get_current_site():
    if getattr(g, 'site', None) is None:
        site_id = current_app.config['SITE_ID']
        g.site, _ = Site.objects.get_or_create(id=site_id, defaults={
            'title': current_app.config.get('SITE_TITLE'),
            'keywords': current_app.config.get('SITE_KEYWORDS', []),
        })
    return g.site


current_site = LocalProxy(get_current_site)


@Dataset.on_delete.connect
def remove_from_home_datasets(dataset):
    if dataset in current_site.settings.home_datasets:
        current_site.settings.home_datasets.remove(dataset)
        current_site.save()


@Reuse.on_delete.connect
def remove_from_home_reuses(reuse):
    if reuse in current_site.settings.home_reuses:
        current_site.settings.home_reuses.remove(reuse)
        current_site.save()
