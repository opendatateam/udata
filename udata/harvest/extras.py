from udata.models import db

from udata.core.dataset.models import Dataset
# from udata.core.dataset.rdf import (
#     dct_issued_from_rdf, dct_modified_from_rdf, landing_page_from_rdf
# )

# Register Protected Extra Field with Embedded Documents
# TODO: how to register additionnal extras (used in plugins for example)


Dataset.harvest.register('created_at', db.DateTimeField)
Dataset.harvest.register('last_modified', db.DateTimeField)
Dataset.harvest.register('landing_page', db.URLField)
Dataset.harvest.register('source_id', db.StringField)
Dataset.harvest.register('remote_id', db.StringField)
Dataset.harvest.register('domain', db.StringField)
Dataset.harvest.register('last_update', db.DateTimeField)
Dataset.harvest.register('remote_url', db.URLField)

Dataset.harvest.register('uri', db.StringField)
Dataset.harvest.register('dct:identifier', db.StringField)


class HarvestExtrasFactory():
    @staticmethod
    def set_extras(harvest=None, created_at=None, last_modified=None, domain=None, remote_id=None,
                   source_id=None, landing_page=None, last_update=None, archived_at=None,
                   archived=None, dct_identifier=None, uri=None):

        # Should we set values or just create the corresponding object?
        # TODO: rename accordingly and protect existing extras

        if not harvest:
            harvest = {}

        if created_at:
            harvest['created_at'] = created_at
        if last_modified:
            harvest['last_modified'] = last_modified
        if landing_page:
            harvest['remote_url'] = landing_page
        if domain:
            harvest['domain'] = domain
        if remote_id:
            harvest['remote_id'] = remote_id
        if source_id:
            harvest['source_id'] = source_id
        if last_update:
            harvest['last_update'] = last_update
        if archived_at:
            harvest['archived_at'] = archived_at
        if archived:
            harvest['archived'] = archived
        if dct_identifier:
            harvest['dct:identifier'] = dct_identifier
        if uri:
            harvest['uri'] = uri

        # harvest.validate()
        return harvest

    @staticmethod
    def unset_extras(harvest, archived_at=False, archived=False):
        if not harvest:
            return

        if archived_at:
            harvest.pop('archived_at', None)

        if archived:
            harvest.pop('archived', None)

        return harvest
