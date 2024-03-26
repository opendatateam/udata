from udata.api import api, fields
from udata.models import db
from bson import ObjectId
import mongoengine

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
            raise ValueError(f"Reference field for '{key}' should have a `nested_fields` argument")

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
    document_keys = set(dir(db.Document))
    keys = [key for key in cls.__dict__.keys() if key not in document_keys]

    read_fields = {}
    write_fields = {}

    read_fields['id'] = fields.String(required=True)

    for key in keys:
        if key == 'objects': continue

        field = getattr(cls, key)
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
                value = [ObjectId(id) for id in value]
            if isinstance(field, mongoengine.fields.ReferenceField):
                value = ObjectId(value)

            setattr(obj, key, value)
