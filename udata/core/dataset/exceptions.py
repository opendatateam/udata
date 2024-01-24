class DatasetException(Exception):
    '''Base class for all dataset exceptions'''
    pass


class ResourceSchemaException(DatasetException):
    '''Raised for resources' schema related exceptions'''
    pass

