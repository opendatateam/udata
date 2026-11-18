class DatasetException(Exception):
    """Base class for all dataset exceptions"""


class ResourceSchemaException(DatasetException):
    """Raised for resources' schema related exceptions"""


class SchemasCatalogNotFoundException(ResourceSchemaException):
    """Raised when the schema catalog cannot be found"""


class SchemasCacheUnavailableException(ResourceSchemaException):
    """Raised when the schema catalog cache is not available or is empty"""
