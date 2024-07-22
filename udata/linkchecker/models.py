from udata.core.dataset.models import ResourceMixin
from udata.mongo import db

# Register harvest extras
ResourceMixin.extras.register("check:available", db.BooleanField)
ResourceMixin.extras.register("check:count-availability", db.IntField)
ResourceMixin.extras.register("check:status", db.IntField)
ResourceMixin.extras.register("check:url", db.StringField)
ResourceMixin.extras.register("check:date", db.DateTimeField)
