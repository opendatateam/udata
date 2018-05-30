class HarvestException(Exception):
    '''Base class for all harvest exception'''
    pass


class HarvestSkipException(HarvestException):
    '''Raised when an item is skipped'''
    pass
