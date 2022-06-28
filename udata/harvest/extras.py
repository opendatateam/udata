from udata.models import db

from udata.core.dataset.models import Dataset, ResourceMixin
# from udata.core.dataset.rdf import (
#     dct_issued_from_rdf, dct_modified_from_rdf, landing_page_from_rdf
# )

# Register Protected Extra Field with Embedded Documents
# TODO: how to register additionnal extras (used in plugins for example)


def dct_modified_from_rdf(rdf):
    dct_modified = rdf_value(rdf, DCT.modified)
    if dct_modified:
        if isinstance(dct_modified, date):
            dct_modified = datetime.combine(dct_modified, datetime.min.time())
        return dct_modified


def dct_issued_from_rdf(rdf):
    dct_issued = rdf_value(rdf, DCT.issued)
    if dct_issued:
        if isinstance(dct_issued, date):
            dct_issued = datetime.combine(dct_issued, datetime.min.time())
        return dct_issued


def landing_page_from_rdf(rdf):
    landing_page = url_from_rdf(rdf, DCAT.landingPage)
    if landing_page:
        try:
            uris.validate(landing_page)
            return landing_page
        except uris.ValidationError:
            pass


class HarvestExtras(db.EmbeddedDocument):
    source_id = db.StringField()
    remote_id = db.StringField()
    domain = db.StringField()
    remote_url = db.URLField()
    last_update = db.DateTimeField()
    created_at = db.DateTimeField()
    last_modified = db.DateTimeField()
    archived_at = db.DateTimeField()
    archived = db.StringField()


class ResourceHarvestExtras(db.EmbeddedDocument):
    created_at = db.DateTimeField()
    modified = db.DateTimeField()


Dataset.protected_extras.register('harvest', HarvestExtras)
ResourceMixin.protected_extras.register('harvest', ResourceHarvestExtras)


class HarvestExtrasFactory():
    @staticmethod
    def set_extras(protected_extras=None, rdf=None, domain=None, remote_id=None, source_id=None,
                   last_update=None, archived_at=None, archived=None, dct_identifier=None,
                   uri=None):

        # Should we set values or just create the corresponding object?
        # TODO: rename accordingly

        if 'harvest' not in protected_extras:
            protected_extras['harvest'] = HarvestExtras()
        harvest_extras = protected_extras['harvest'].copy()

        if rdf:
            created_at = dct_issued_from_rdf(rdf)
            if created_at:
                harvest_extras.created_at = created_at

            last_modified = dct_modified_from_rdf(rdf)
            if last_modified:
                harvest_extras.last_modified = last_modified

            landing_page = landing_page_from_rdf(rdf)
            if landing_page:
                harvest_extras.remote_url = landing_page

        if domain:
            harvest_extras.domain = domain

        if remote_id:
            harvest_extras.remote_id = remote_id

        if source_id:
            harvest_extras.source_id = source_id

        if last_update:
            harvest_extras.last_update = last_update

        if archived_at:
            harvest_extras.archived_at = archived_at

        if archived:
            harvest_extras.archived = archived

        if dct_identifier:
            harvest_extras.dct_identifier = dct_identifier

        if uri:
            harvest_extras.uri = uri

        harvest_extras.validate()
        return harvest_extras

    @staticmethod
    def unset_extras(protected_extras, archived_at=False, archived=False):
        if 'harvest' not in protected_extras:
            return
        harvest_extras = protected_extras['harvest'].copy()

        if archived_at:
            harvest_extras.archived_at = None

        if archived:
            harvest_extras.archived = None

        return harvest_extras


# protected_extras = FactoryExtras(read_only_protected_extras, parse_distrib, moissonneur, distrib, )
# dataset.protected_extras = protected_extras
# dataset.save()

