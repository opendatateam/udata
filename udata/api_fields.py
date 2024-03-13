from udata.api import api, fields
from udata.models import db
from bson import ObjectId
import mongoengine

def convert_db_to_field(key, field):
    info = getattr(field, '__additional_field_info__', {})

    params = {}
    params['required'] = field.required

    if info.get('convert_to'):
        return info.get('convert_to')
    elif isinstance(field, db.StringField):
        constructor = fields.String
        params['min_length'] = field.min_length
        params['max_length'] = field.max_length
    elif isinstance(field, db.FloatField):
        constructor = fields.Float
        params['min'] = field.min
        params['max'] = field.max
    elif isinstance(field, db.BooleanField):
        constructor = fields.Boolean
    elif isinstance(field, db.DateTimeField):
        constructor = fields.ISODateTime
    elif isinstance(field, db.DictField):
        constructor = fields.Raw
    elif isinstance(field, db.ListField):
        nested_field = convert_db_to_field(f"{key}.inner", field.field)
        constructor = lambda **kwargs: fields.List(nested_field, **kwargs)
    elif isinstance(field, db.ReferenceField):
        nested_fields = info.get('nested_fields')
        if nested_fields is None:
            raise ValueError(f"Reference field for '{key}' should have a `nested_fields` argument")

        constructor = lambda **kwargs: fields.Nested(nested_fields, **kwargs)
    else:
        raise ValueError(f"Unsupported MongoEngine field type {field.__class__.__name__}")
    
    params = {**params, **info}
    return constructor(**params)

def generate_fields(cls):
    document_keys = set(dir(db.Document))
    keys = [key for key in cls.__dict__.keys() if key not in document_keys]

    cls_fields = {}

    for key in keys:
        if key == 'objects': continue

        field = getattr(cls, key)
        if not hasattr(field, '__additional_field_info__'): continue 

        cls_fields[key] = convert_db_to_field(key, field)

    cls.__fields__ = api.model(cls.__name__, cls_fields)
    return cls

def field(inner, **kwargs):
    inner.__additional_field_info__ = kwargs
    return inner


def patch(obj, request): 
    for key, value in request.json.items():
        field = obj.__fields__.get(key)
        if field is not None and not field.readonly:
            model_attribute = getattr(obj.__class__, key)
            if isinstance(model_attribute, mongoengine.fields.ListField) and isinstance(model_attribute.field, mongoengine.fields.ReferenceField):
                value = [ObjectId(id) for id in value]
            if isinstance(field, mongoengine.fields.ReferenceField):
                value = ObjectId(value)

            setattr(obj, key, value)
