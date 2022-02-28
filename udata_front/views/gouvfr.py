import frontmatter
import logging
import requests

from flask import url_for, redirect, abort, current_app
from jinja2.exceptions import TemplateNotFound
from mongoengine.errors import ValidationError

from udata_front import theme
from udata_front.theme import theme_static_with_version
from udata.app import cache
from udata.frontend import template_hook
from udata.models import Reuse, Dataset
from udata.i18n import I18nBlueprint

from udata_front import APIGOUVFR_EXTRAS_KEY

log = logging.getLogger(__name__)

blueprint = I18nBlueprint('gouvfr', __name__,
                          template_folder='../templates',
                          static_folder='../static',
                          static_url_path='/static/gouvfr')

PAGE_CACHE_DURATION = 60 * 5  # in seconds


@blueprint.route('/dataset/<dataset>/')
def redirect_datasets(dataset):
    '''Route Legacy CKAN datasets'''
    return redirect(url_for('datasets.show', dataset=dataset))


@blueprint.route('/organization/')
def redirect_organizations_list():
    '''Route legacy CKAN organizations listing'''
    return redirect(url_for('organizations.list'))


@blueprint.route('/organization/<org>/')
def redirect_organizations(org):
    '''Route legacy CKAN organizations'''
    return redirect(url_for('organizations.show', org=org))


@blueprint.route('/group/<topic>/')
def redirect_topics(topic):
    '''Route legacy CKAN topics'''
    return redirect(url_for('topics.display', topic=topic))


def get_pages_gh_urls(slug):
    repo = current_app.config.get('PAGES_GH_REPO_NAME')
    if not repo:
        abort(404)
    branch = current_app.config.get('PAGES_REPO_BRANCH', 'master')
    raw_url = f'https://raw.githubusercontent.com/{repo}/{branch}/pages/{slug}.md'
    gh_url = f'https://github.com/{repo}/blob/{branch}/pages/{slug}.md'
    return raw_url, gh_url


@cache.memoize(PAGE_CACHE_DURATION)
def get_page_content(slug):
    '''
    Get a page content from gh repo (md).
    This has a double layer of cache:
    - @cache.cached decorator w/ short lived cache for normal operations
    - a long terme cache w/o timeout to be able to always render some content
    '''
    cache_key = f'pages-content-{slug}'
    raw_url, gh_url = get_pages_gh_urls(slug)
    try:
        response = requests.get(raw_url, timeout=5)
        # do not cache 404 and forward status code
        if response.status_code == 404:
            abort(404)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.exception(f'Error while getting {slug} page from gh: {e}')
        content = cache.get(cache_key)
    else:
        content = response.text
        cache.set(cache_key, content)
    # no cached version or no content from gh
    if not content:
        log.error(f'No content found inc. from cache for page {slug}')
        abort(503)
    return content, gh_url


def get_object(model, id_or_slug):
    objects = getattr(model, 'objects')
    obj = objects.filter(slug=id_or_slug).first()
    if not obj:
        try:
            obj = objects.filter(id=id_or_slug).first()
        except ValidationError:
            pass
    return obj


@blueprint.route('/pages/<path:slug>/')
def show_page(slug):
    content, gh_url = get_page_content(slug)
    page = frontmatter.loads(content)
    reuses = [get_object(Reuse, r) for r in page.get('reuses') or []]
    datasets = [get_object(Dataset, d) for d in page.get('datasets') or []]
    reuses = [r for r in reuses if r is not None]
    datasets = [d for d in datasets if d is not None]
    return theme.render(
        'page.html',
        page=page, reuses=reuses, datasets=datasets, gh_url=gh_url
    )


@blueprint.route('/suivi/')
def suivi():
    try:
        return theme.render('suivi.html')
    except TemplateNotFound:
        abort(404)


def has_apis(ctx):
    dataset = ctx['dataset']
    return dataset.extras.get(APIGOUVFR_EXTRAS_KEY, [])


@template_hook('dataset.display.after-description', when=has_apis)
def dataset_apis(ctx):
    dataset = ctx['dataset']
    return theme.render('dataset-apis.html', apis=dataset.extras.get(APIGOUVFR_EXTRAS_KEY))


@template_hook('oauth_authorize_theme_content')
def oauth_authorize_theme_content(ctx):
    grant = ctx['grant']
    return theme.render('api/oauth_authorize.html', grant=grant)


@template_hook('oauth_error_theme_content')
def oauth_error_theme_content(ctx):
    request = ctx['request']
    return theme.render('api/oauth_error.html', error=request.args.get('error'))


# TODO : better this, redirect is not the best. How to serve it instead ?!
@blueprint.route('/_stylemark/<path:filename>/')
def stylemark(filename):
    return redirect(theme_static_with_version(None,
                                              filename="stylemark/index.html"))
