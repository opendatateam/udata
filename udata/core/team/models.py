from udata.models import db


__all__ = (
    'Team', 'TITLE_SIZE_LIMIT', 'DESCRIPTION_SIZE_LIMIT'
)


TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000


class Team(db.Document):
    name = db.StringField(required=True)
    slug = db.SlugField(
        max_length=255, required=True, populate_from='name', update=True,
        unique=False)
    description = db.StringField()

    members = db.ListField(db.ReferenceField('User'))

    def member(self, user):
        for member in self.members:
            if member == user:
                return member
        return None

    def is_member(self, user):
        return self.member(user) is not None
