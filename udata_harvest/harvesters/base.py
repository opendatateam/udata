# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

import requests

from ..models import HarvestItem, HarvestJob

log = logging.getLogger(__name__)


class BaseHarvester(object):
    '''Base class for Harvester implementations'''
    #: A machine-readable name for configuration references.
    name = None
    #: A human-readable name for Web UI.
    title = None
    #: A short description.
    description = None
    verify_ssl = True

    def __init__(self, source):
        self.source = source

    @property
    def config(self):
        return self.source.config

    @property
    def job(self):
        return self.source.jobs[-1] if self.source.jobs else None

    def get(self, url, **kwargs):
        headers = self.get_headers()
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def get_headers(self):
        return {
            'User-Agent': 'uData/0.1 {0.name}'.format(self),  # TODO: extract site title and version
        }

    def harvest(self, async=False):
        '''Start the harvesting process'''
        self.handle_initialization()
        self.process_items()

    def handle_initialization(self):
        '''Initialize the harvesting for a given job'''
        log.debug('Initializing backend')
        self.initialize()
        if self.queue:
            log.debug('Queued %s items', len(self.queue))

    def process_items(self):
        '''Process the data identified in the initialize stage'''
        for item in self.job.items:
            try:
                obj = self.process(item)
                log.debug('Processed %s', obj)
                obj.validate()
            except:
                log.exception('Unable to parse %s', self.remote_url(item) or item)

    def add_item(self, remote_id):
        self.job.items.append(HarvestItem(remote_id=remote_id))

    def validate(self, config):
        '''
        An optionnal validation method for the configuration.

        It will be used on form validation and on each job start.
        It should raise Exceptions on error.
        '''

    def remote_url(self, item):
        '''
        Optionnaly provide a remote URL for an HarvestItem.

        :param item: an HarvestItem
        :returns: A string with the URL to the original document
        '''

    def initialize(self, job):
        '''
        This method is responsible for:
            - gathering all the necessary objects to fetch on a later.
              stage (e.g. for a CSW server, perform a GetRecords request)
            - creating the necessary HarvestItem. The HarvestItem need a
              reference date with the last modified date for the resource, this
              may need to be set in a different stage depending on the type of
              source.
            - creating and storing any suitable HarvestErrors that may occur.

        :param harvest_job: HarvestJob object
        :returns: A list of HarvestObject ids
        '''
        raise NotImplementedError

    def process(self, item):
        '''
        This method is responsible for:
            - getting the contents of the remote item.
            - creating or updating a local object
            - raising any HarvestError that may occur.
            - returning True if everything went as expected, False otherwise.

        :param item: HarvestItem object
        :returns: True if everything went right, False if errors were found
        '''
        raise NotImplementedError

    def _save_gather_error(self, message, job):
        err = HarvestGatherError(message=message, job=job)
        try:
            err.save()
        except InvalidRequestError:
            Session.rollback()
            err.save()
        finally:
            log.error(message)


    def _save_object_error(self, message, obj, stage=u'Fetch', line=None):
        err = HarvestObjectError(message=message,
                                 object=obj,
                                 stage=stage,
                                 line=line)
        try:
            err.save()
        except InvalidRequestError, e:
            Session.rollback()
            err.save()
        finally:
            log_message = '{0}, line {1}'.format(message,line) if line else message
            log.debug(log_message)


    def _create_harvest_objects(self, remote_ids, harvest_job):
        '''
        Given a list of remote ids and a Harvest Job, create as many Harvest Objects and
        return a list of their ids to be passed to the fetch stage.

        TODO: Not sure it is worth keeping this function
        '''
        try:
            object_ids = []
            if len(remote_ids):
                for remote_id in remote_ids:
                    # Create a new HarvestObject for this identifier
                    obj = HarvestObject(guid = remote_id, job = harvest_job)
                    obj.save()
                    object_ids.append(obj.id)
                return object_ids
            else:
               self._save_gather_error('No remote datasets could be identified', harvest_job)
        except Exception, e:
            self._save_gather_error('%r' % e.message, harvest_job)


    def _create_or_update_package(self, package_dict, harvest_object):
        '''
        Creates a new package or updates an exisiting one according to the
        package dictionary provided. The package dictionary should look like
        the REST API response for a package:

        http://ckan.net/api/rest/package/statistics-catalunya

        Note that the package_dict must contain an id, which will be used to
        check if the package needs to be created or updated (use the remote
        dataset id).

        If the remote server provides the modification date of the remote
        package, add it to package_dict['metadata_modified'].


        TODO: Not sure it is worth keeping this function. If useful it should
        use the output of package_show logic function (maybe keeping support
        for rest api based dicts
        '''
        try:
            # Change default schema
            schema = default_create_package_schema()
            schema['id'] = [ignore_missing, unicode]
            schema['__junk'] = [ignore]

            # Check API version
            if self.config:
                try:
                    api_version = int(self.config.get('api_version', 2))
                except ValueError:
                    raise ValueError('api_version must be an integer')

                #TODO: use site user when available
                user_name = self.config.get('user', u'harvest')
            else:
                api_version = 2
                user_name = u'harvest'

            context = {
                'model': model,
                'session': Session,
                'user': user_name,
                'api_version': api_version,
                'schema': schema,
                'ignore_auth': True,
            }

            if self.config and self.config.get('clean_tags', False):
                tags = package_dict.get('tags', [])
                tags = [munge_tag(t) for t in tags if munge_tag(t) != '']
                tags = list(set(tags))
                package_dict['tags'] = tags

            # Check if package exists
            data_dict = {}
            data_dict['id'] = package_dict['id']
            try:
                existing_package_dict = get_action('package_show')(context, data_dict)

                # In case name has been modified when first importing. See issue #101.
                package_dict['name'] = existing_package_dict['name']

                # Check modified date
                if not 'metadata_modified' in package_dict or \
                   package_dict['metadata_modified'] > existing_package_dict.get('metadata_modified'):
                    log.info('Package with GUID %s exists and needs to be updated' % harvest_object.guid)
                    # Update package
                    context.update({'id':package_dict['id']})
                    package_dict.setdefault('name',
                            existing_package_dict['name'])
                    new_package = get_action('package_update_rest')(context, package_dict)

                else:
                    log.info('Package with GUID %s not updated, skipping...' % harvest_object.guid)
                    return

                # Flag the other objects linking to this package as not current anymore
                from ckanext.harvest.model import harvest_object_table
                conn = Session.connection()
                u = update(harvest_object_table) \
                        .where(harvest_object_table.c.package_id==bindparam('b_package_id')) \
                        .values(current=False)
                conn.execute(u, b_package_id=new_package['id'])

                # Flag this as the current harvest object

                harvest_object.package_id = new_package['id']
                harvest_object.current = True
                harvest_object.save()

            except NotFound:
                # Package needs to be created

                # Get rid of auth audit on the context otherwise we'll get an
                # exception
                context.pop('__auth_audit', None)

                # Set name if not already there
                package_dict.setdefault('name', self._gen_new_name(package_dict['title']))

                log.info('Package with GUID %s does not exist, let\'s create it' % harvest_object.guid)
                harvest_object.current = True
                harvest_object.package_id = package_dict['id']
                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                harvest_object.add()

                model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                model.Session.flush()

                new_package = get_action('package_create_rest')(context, package_dict)

            Session.commit()

            return True

        except ValidationError,e:
            log.exception(e)
            self._save_object_error('Invalid package with GUID %s: %r'%(harvest_object.guid,e.error_dict),harvest_object,'Import')
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r'%e,harvest_object,'Import')

        return None
