from udata.api import api
import flask_restx.fields as restx_fields
import udata.api.fields as custom_restx_fields
from bson import ObjectId
import mongoengine
import mongoengine.fields as mongo_fields

from udata.mongo.errors import FieldValidationError

def convert_db_to_field(key, field, info = {}):
    '''
    This function maps a Mongo field to a Flask RestX field.
    Most of the types are a simple 1-to-1 mapping except lists and references that requires
    more work.
    We currently only map the params that we use from Mongo to RestX (for example min_length / max_length…).

    In the first part of the function we save the RestX constructor as a lambda because we need to call it with the
    params. Since merging the params involve a litte bit of work (merging default params with read/write params and then with
    user-supplied overrides, setting the readonly flag…), it's easier to have do this one time at the end of the function.
    '''
    info = { **getattr(field, '__additional_field_info__', {}), **info }

    params = {}
    params['required'] = field.required

    read_params = {}
    write_params = {}

    constructor = None
    constructor_read = None
    constructor_write = None

    if info.get('convert_to'):
        # TODO: this is currently never used. We may remove it if the auto-conversion
        # is always good enough.
        return info.get('convert_to'), info.get('convert_to')
    elif isinstance(field, mongo_fields.StringField):
        constructor = restx_fields.String
        params['min_length'] = field.min_length
        params['max_length'] = field.max_length
    elif isinstance(field, mongo_fields.FloatField):
        constructor = restx_fields.Float
        params['min'] = field.min # TODO min_value?
        params['max'] = field.max
    elif isinstance(field, mongo_fields.BooleanField):
        constructor = restx_fields.Boolean
    elif isinstance(field, mongo_fields.DateTimeField):
        constructor = custom_restx_fields.ISODateTime
    elif isinstance(field, mongo_fields.DictField):
        constructor = restx_fields.Raw
    elif isinstance(field, mongo_fields.ListField):
        # For lists, we convert the inner value from Mongo to RestX then we create
        # the `List` RestX type with this converted inner value.
        field_read, field_write = convert_db_to_field(f"{key}.inner", field.field, info.get('inner_field_info', {}))
        constructor_read = lambda **kwargs: restx_fields.List(field_read, **kwargs)
        constructor_write = lambda **kwargs: restx_fields.List(field_write, **kwargs)
    elif isinstance(field, mongo_fields.ReferenceField):
        # For reference we accept while writing a String representing the ID of the referenced model.
        # For reading, if the user supplied a `nested_fields` (RestX model), we use it to convert
        # the referenced model, if not we return a String (and RestX will call the `str()` of the model
        # when returning from an endpoint)
        nested_fields = info.get('nested_fields')
        if nested_fields is None:
            # If there is no `nested_fields` convert the object to the string representation.
            constructor_read = restx_fields.String
        else:
            constructor_read = lambda **kwargs: restx_fields.Nested(nested_fields, **kwargs)

        write_params['description'] = "ID of the reference"
        constructor_write = restx_fields.String
    elif isinstance(field, mongo_fields.EmbeddedDocumentField):
        nested_fields = info.get('nested_fields')
        if nested_fields is None:
            raise ValueError(f"EmbeddedDocumentField `{key}` requires a `nested_fields` param to serialize/deserialize.")

        constructor = lambda **kwargs: restx_fields.Nested(nested_fields, **kwargs)
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

def generate_fields(**kwargs):
    '''
    This decorator will create two auto-generated attributes on the class `__read_fields__` and `__write_fields__`
    that can be used in API endpoint inside `expect()` and `marshall_with()`.
    '''
    def wrapper(cls):
        read_fields = {}
        write_fields = {}
        sortables = []

        read_fields['id'] = restx_fields.String(required=True)

        for key, field in cls._fields.items():
            info = getattr(field, '__additional_field_info__', None)
            if info is None: continue 

            if info.get('sortable', False):
                sortables.append(key)

            read, write = convert_db_to_field(key, field)

            if read:
                read_fields[key] = read
            if write:
                write_fields[key] = write

        # The goal of this loop is to fetch all functions (getters) of the class
        # If a function has an `__additional_field_info__` attribute it means 
        # it has been decorated with `@function_field()` and should be included
        # in the API response.
        for method_name in dir(cls):
            if method_name == 'objects': continue
            if method_name.startswith('_'): continue
            if method_name in read_fields: continue # Do not override if the attribute is also callable like for Extras

            method = getattr(cls, method_name)
            if not callable(method): continue

            info = getattr(method, '__additional_field_info__', None)
            if info is None: continue

            def make_lambda(method):
                '''
                Factory function to create a lambda with the correct scope.
                If we don't have this factory function, the `method` will be the 
                last method assigned in this loop?
                '''
                return lambda o: method(o)

            read_fields[method_name] = restx_fields.String(attribute=make_lambda(method), **{ 'readonly':True, **info })


        cls.__read_fields__ = api.model(f"{cls.__name__} (read)", read_fields, **kwargs)
        cls.__write_fields__ = api.model(f"{cls.__name__} (write)", write_fields, **kwargs)

        mask = kwargs.pop('mask', None)
        if mask is not None:
            mask = 'data{{{0}}},*'.format(mask)
        cls.__page_fields__ = api.model(f"{cls.__name__}Page", custom_restx_fields.pager(cls.__read_fields__), mask=mask, **kwargs)

        # Parser for index sort/filters
        paginable = kwargs.get('paginable', True)
        parser = api.parser()

        if paginable:
            parser.add_argument('page', type=int, location='args', default=1, help='The page to display')
            parser.add_argument('page_size', type=int, location='args', default=20, help='The page size')
        
        if sortables:
            choices = sortables + ['-' + k for k in sortables]
            parser.add_argument('sort', type=str, location='args', choices=choices, help='The field (and direction) on which sorting apply')

        cls.__index_parser__ = parser
        def apply_sort_filters_and_pagination(base_query):
            args = cls.__index_parser__.parse_args()

            if sortables and args['sort']:
                base_query = base_query.order_by(args['sort'])

            if paginable:
                base_query = base_query.paginate(args['page'], args['page_size'])

            return base_query

        cls.apply_sort_filters_and_pagination = apply_sort_filters_and_pagination
        return cls
    return wrapper


def function_field(**info):
    def inner(func):
        func.__additional_field_info__ = info
        return func

    return inner

def field(inner, **kwargs):
    '''
    Simple decorator to mark a field as visible for the API fields.
    We can pass additional arguments that will be forward to the RestX field constructor.
    '''
    inner.__additional_field_info__ = kwargs
    return inner


def patch(obj, request): 
    '''
    Patch the object with the data from the request.
    Only fields decorated with the `field()` decorator will be read (and not readonly).
    '''
    for key, value in request.json.items():
        field = obj.__write_fields__.get(key)
        if field is not None and not field.readonly:
            model_attribute = getattr(obj.__class__, key)
            if isinstance(model_attribute, mongoengine.fields.ListField) and isinstance(model_attribute.field, mongoengine.fields.ReferenceField):
                # TODO `wrap_primary_key` do Mongo request, do a first pass to fetch all documents before calling it (to avoid multiple queries).
                value = [wrap_primary_key(key, model_attribute.field, id) for id in value]
            if isinstance(model_attribute, mongoengine.fields.ReferenceField):
                value = wrap_primary_key(key, model_attribute, value)


            info = getattr(model_attribute, '__additional_field_info__', {})

            # `check` field attribute allows to do validation from the request before setting
            # the attribute
            check = info.get('check', None)
            if check is not None:
                check(**{key: value}) # TODO add other model attributes in function parameters

            setattr(obj, key, value)

    return obj

def wrap_primary_key(field_name: str, foreign_field: mongoengine.fields.ReferenceField, value: str):
    '''
    We need to wrap the `String` inside an `ObjectId` most of the time. If the foreign ID is a `String` we need to get 
    a `DBRef` from the database.

    TODO: we only check the document reference if the ID is a `String` field (not in the case of a classic `ObjectId`).
    '''
    document_type = foreign_field.document_type()
    id_field_name = document_type.__class__._meta["id_field"]

    id_field = getattr(document_type.__class__, id_field_name)

    # Get the foreign document from MongoDB because the othewise it fails during read
    # Also useful to get a DBRef for non ObjectId references (see below)
    foreign_document = document_type.__class__.objects(**{id_field_name: value}).first()
    if foreign_document is None:
        raise FieldValidationError(field=field_name, message=f"Unknown reference '{value}'")
    
    if isinstance(id_field, mongoengine.fields.ObjectIdField):
        return ObjectId(value)
    elif isinstance(id_field, mongoengine.fields.StringField):
        # Right now I didn't find a simpler way to make mongoengine happy.
        # For references, it expects `ObjectId`, `DBRef`, `LazyReference` or `document` but since
        # the primary key a StringField (not an `ObjectId`) we cannot create an `ObjectId`, I didn't find
        # a way to create a `DBRef` nor a `LazyReference` so I create a simple document with only the ID field.
        # We could use a simple dict as follow instead:
        # { 'id': value }
        # … but it may be important to check before-hand that the reference point to a correct document.
        return foreign_document.to_dbref()
    else:
        raise ValueError(f"Unknown ID field type {id_field.__class__} for {document_type.__class__} (ID field name is {id_field_name}, value was {value})")

