class DatasetException(Exception):
    '''Base class for all dataset exceptions'''
    pass


class ResourceSchemaException(DatasetException):
    '''Raised for resources' schema related exceptions'''
    pass


class SchemasCatalogNotFoundException(ResourceSchemaException):
    '''Raised when the schema catalog cannot be found'''
    pass


class SchemasCacheUnavailableException(ResourceSchemaException):
    '''Raised when the schema catalog cache is not available or is empty'''
    pass
