from udata.models import db, WithMetrics


class FakeModel(WithMetrics, db.Document):
    name = db.StringField()

    def __unicode__(self):
        return self.name or ''
