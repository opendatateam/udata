from mongoengine.base import get_document
from mongoengine.errors import NotRegistered

from udata.flask_mongoengine.engine import MongoEngine


class UDataMongoEngine(MongoEngine):
    """Customized mongoengine with extra fields types and helpers"""

    def resolve_model(self, model):
        """
        Resolve a model given a name or dict with `class` entry.

        :raises ValueError: model specification is wrong or does not exists
        """
        if not model:
            raise ValueError("Unsupported model specifications")
        if isinstance(model, str):
            classname = model
        elif isinstance(model, dict) and "class" in model:
            classname = model["class"]
        else:
            raise ValueError("Unsupported model specifications")

        try:
            return get_document(classname)
        except NotRegistered:
            message = 'Model "{0}" does not exist'.format(classname)
            raise ValueError(message)


db = UDataMongoEngine()
