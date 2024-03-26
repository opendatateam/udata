from udata.api import api, fields
from udata.models import db
from bson import ObjectId
import mongoengine

from udata.models import FieldValidationError

def convert_db_to_field(key, field):
    info = getattr(field, '__additional_field_info__', {})

    params = {}
    params['required'] = field.required

    read_params = {}
    write_params = {}

    constructor = None
    constructor_read = None
    constructor_write = None

    if info.get('convert_to'):
        return info.get('convert_to'), info.get('convert_to')
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
        field_read, field_write = convert_db_to_field(f"{key}.inner", field.field)
        constructor_read = lambda **kwargs: fields.List(field_read, **kwargs)
        constructor_write = lambda **kwargs: fields.List(field_write, **kwargs)
    elif isinstance(field, db.ReferenceField):
        nested_fields = info.get('nested_fields')
        if nested_fields is None:
            # If there is no `nested_fields` convert the object to the string representation.
            constructor_read = fields.String
        else:
            constructor_read = lambda **kwargs: fields.Nested(nested_fields, **kwargs)

        
        write_params['description'] = "ID of the reference"
        constructor_write = fields.String
    else:
        raise ValueError(f"Unsupported MongoEngine field type {field.__class__.__name__}")
    
    read_params = {**params, **read_params, **info}
    write_params = {**params, **write_params, **info}

    read = constructor_read(**read_params) if constructor_read else constructor(**read_params)
    if write_params.get('readonly', False):
        write = None
    else:
        write = constructor_write(**write_params) if constructor_write else constructor(**write_params)
    return read, write

def generate_fields(cls):
    read_fields = {}
    write_fields = {}

    read_fields['id'] = fields.String(required=True)

    for key, field in cls._fields.items():
        if not hasattr(field, '__additional_field_info__'): continue 

        read, write = convert_db_to_field(key, field)

        if read:
            read_fields[key] = read
        if write:
            write_fields[key] = write

    cls.__read_fields__ = api.model(f"{cls.__name__} (read)", read_fields)
    cls.__write_fields__ = api.model(f"{cls.__name__} (write)", write_fields)
    return cls

def field(inner, **kwargs):
    inner.__additional_field_info__ = kwargs
    return inner


def patch(obj, request): 
    for key, value in request.json.items():
        field = obj.__write_fields__.get(key)
        if field is not None and not field.readonly:
            model_attribute = getattr(obj.__class__, key)
            if isinstance(model_attribute, mongoengine.fields.ListField) and isinstance(model_attribute.field, mongoengine.fields.ReferenceField):
                # TODO `wrap_primary_key` do Mongo request, do a first pass to fetch all documents before calling it (to avoid multiple queries).
                value = [wrap_primary_key(key, model_attribute.field, id) for id in value]
            if isinstance(model_attribute, mongoengine.fields.ReferenceField):
                value = wrap_primary_key(key, model_attribute, value)

            setattr(obj, key, value)

    return obj

def wrap_primary_key(field_name: str, foreign_field: mongoengine.fields.ReferenceField, value: str):
    document_type = foreign_field.document_type()
    id_field_name = document_type.__class__._meta["id_field"]

    id_field = getattr(document_type.__class__, id_field_name)

    if isinstance(id_field, mongoengine.fields.ObjectIdField):
        return ObjectId(value)
    elif isinstance(id_field, mongoengine.fields.StringField):
        # Right now I didn't find a simpler way to make mongoengine happy.
        # For references, it expects `ObjectId`, `DBRef`, `LazyReference` or `document` but since
        # the primary key a StringField (not an `ObjectId`) we cannot create an `ObjectId`, I didn't find
        # a way to create a `DBRef` nor a `LazyReference` so I create a simple document with only the ID field.
        document = document_type.__class__.objects(**{id_field_name: value}).first()
        if document is None:
            raise FieldValidationError(field=field_name, message=f"Unknown reference '{value}'")

        return document.to_dbref()
    else:
        raise ValueError(f"Unknown ID field type {id_field.__class__} for {document_type.__class__} (ID field name is {id_field_name}, value was {value})")

