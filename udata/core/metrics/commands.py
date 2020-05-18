import logging

import click

from flask import current_app

from udata.commands import cli, success, echo, white
from udata.models import User, Dataset, Reuse, Organization, Site

log = logging.getLogger(__name__)


@cli.group('metrics')
def grp():
    '''Metrics related operations'''
    pass


@grp.command()
@click.option('-s', '--site', is_flag=True, help='Update site metrics')
@click.option('-o', '--organizations', is_flag=True,
              help='Compute organizations metrics')
@click.option('-d', '--datasets', is_flag=True,
              help='Compute datasets metrics')
@click.option('-r', '--reuses', is_flag=True, help='Compute reuses metrics')
@click.option('-u', '--users', is_flag=True, help='Compute users metrics')
@click.option('--drop', is_flag=True, help='Clear old metrics before computing new ones')
def update(site=False, organizations=False, users=False, datasets=False,
           reuses=False, drop=False):
    '''Update all metrics for the current date'''
    do_all = not any((site, organizations, users, datasets, reuses))

    if do_all or site:
        log.info('Update site metrics')
        try:
            site = Site.objects(id=current_app.config['SITE_ID']).first()
            if drop:
                site.metrics.clear()
            site.count_users()
            site.count_org()
            site.count_datasets()
            site.count_resources()
            site.count_reuses()
            site.count_followers()
            site.count_discussions()
            site.count_max_dataset_followers()
            site.count_max_dataset_reuses()
            site.count_max_reuse_datasets()
            site.count_max_reuse_followers()
            site.count_max_org_followers()
            site.count_max_org_reuses()
            site.count_max_org_datasets()
        except Exception as e:
            log.info(f'Error during update: {e}')


    if do_all or datasets:
        log.info('Update datasets metrics')
        all_datasets = Dataset.objects.visible().timeout(False)
        with click.progressbar(all_datasets, length=Dataset.objects.count()) as dataset_bar:
            for dataset in dataset_bar:
                try:
                    if drop:
                        dataset.metrics.clear()
                    dataset.count_discussions()
                    dataset.count_issues()
                    dataset.count_reuses()
                    dataset.count_followers()
                except Exception as e:
                    log.info(f'Error during update: {e}')
                    continue

    if do_all or reuses:
        log.info('Update reuses metrics')
        all_reuses = Reuse.objects.visible().timeout(False)
        with click.progressbar(all_reuses, length=Reuse.objects.visible().count()) as reuses_bar:
            for reuse in reuses_bar:
                try:
                    if drop:
                        reuse.metrics.clear()
                    reuse.count_discussions()
                    reuse.count_issues()
                    reuse.count_followers()
                except Exception as e:
                    log.info(f'Error during update: {e}')
                    continue

    if do_all or organizations:
        log.info('Update organizations metrics')
        all_org = Organization.objects.visible().timeout(False)
        with click.progressbar(all_org, length=Organization.objects.visible().count()) as org_bar:
            for organization in org_bar:
                try:
                    if drop:
                        organization.metrics.clear()
                    organization.count_datasets()
                    organization.count_reuses()
                    organization.count_followers()
                except Exception as e:
                    log.info(f'Error during update: {e}')
                    continue

    if do_all or users:
        log.info('Update user metrics')
        all_users = User.objects.timeout(False)
        with click.progressbar(all_users, length=User.objects.count()) as users_bar:
            for user in users_bar:
                try:
                    if drop:
                        user.metrics.clear()
                    user.count_datasets()
                    user.count_reuses()
                    user.count_followers()
                    user.count_following()
                except Exception as e:
                    log.info(f'Error during update: {e}')
                    continue
    success('All metrics have been updated')
