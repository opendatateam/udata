import os

from datetime import datetime

from babel.messages.pofile import read_po, write_po
from babel.util import LOCALTZ
from invoke import task, call

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))

I18N_ROOT = 'udata_front/theme/gouvfr/translations'

THEME_ROOT = os.path.join(ROOT, 'udata_front/theme', 'gouvfr')

LANGUAGES = ['fr']

TO_CLEAN = ['build', 'dist', '**/*.pyc', 'reports']


def color(code):
    '''A simple ANSI color wrapper factory'''
    return lambda t: '\033[{0}{1}\033[0;m'.format(code, t)


green = color('1;32m')
red = color('1;31m')
blue = color('1;30m')
cyan = color('1;36m')
purple = color('1;35m')
white = color('1;39m')


def header(text):
    '''Display an header'''
    print(' '.join((blue('>>'), cyan(text))))


def info(text, *args, **kwargs):
    '''Display informations'''
    text = text.format(*args, **kwargs)
    print(' '.join((purple('>>>'), text)))


def success(text):
    '''Display a success message'''
    print(' '.join((green('>>'), white(text))))


def error(text):
    '''Display an error message'''
    print(red('✘ {0}'.format(text)))


@task
def clean(ctx):
    '''Cleanup all build artifacts'''
    header(clean.__doc__)
    with ctx.cd(ROOT):
        for pattern in TO_CLEAN:
            info('Removing {0}', pattern)
            ctx.run('rm -rf {0}'.format(pattern))


@task
def test(ctx, report=False):
    '''Run tests suite'''
    cmd = 'pytest -v'
    if report:
        cmd = ' '.join((cmd, '--junitxml=reports/tests.xml'))
    with ctx.cd(ROOT):
        ctx.run(cmd, pty=True)


@task
def cover(ctx, html=False, report=True):
    '''Run tests suite with coverage'''
    cmd = 'pytest --cov udata_front --cov-report term'
    if report:
        cmd = ' '.join((cmd, '--junitxml=reports/tests.xml'))
    if html:
        cmd = ' '.join((cmd, '--cov-report html:reports/cover'))
    with ctx.cd(ROOT):
        ctx.run(cmd, pty=True)


@task
def qa(ctx):
    '''Run a quality report'''
    header(qa.__doc__)
    with ctx.cd(ROOT):
        info('Python Static Analysis')
        flake8_results = ctx.run('flake8 udata_front', pty=True, warn=True)
        if flake8_results.failed:
            error('There is some lints to fix')
        else:
            success('No lint to fix')
        info('Ensure PyPI can render README and CHANGELOG')
        readme_results = ctx.run('python setup.py check -m -s', pty=True, warn=True, hide=True)
        if readme_results.failed:
            print(readme_results.stdout)
            error('README and/or CHANGELOG is not renderable by PyPI')
        else:
            success('README and CHANGELOG are renderable by PyPI')
    if flake8_results.failed or readme_results.failed:
        error('Quality check failed')
        exit(flake8_results.return_code or readme_results.return_code)
    success('Quality check OK')


def set_po_metadata(filename, locale):
    # Fix crowdin requiring Language with `2-digit` iso code in potfile
    # to produce 2-digit iso code pofile
    # Opening the catalog also allows to set extra metadata
    with open(filename, 'rb') as infile:
        catalog = read_po(infile, locale)
    catalog.copyright_holder = 'Etalab'
    catalog.msgid_bugs_address = 'data.gouv@data.gouv.fr'
    catalog.language_team = 'Data.gouv.fr Team <data.gouv@data.gouv.fr>'
    catalog.last_translator = 'Data.gouv.fr Team <data.gouv@data.gouv.fr>'
    catalog.revision_date = datetime.now(LOCALTZ)
    with open(filename, 'wb') as outfile:
        write_po(outfile, catalog, width=80)


@task
def i18n(ctx, update=False):
    '''Extract translatable strings'''
    header(i18n.__doc__)

    # Python translations
    # TODO: Make it generic for any theme
    info('Extract python translations')
    with ctx.cd(ROOT):
        ctx.run('python setup.py extract_messages')
        set_po_metadata(os.path.join(I18N_ROOT, 'gouvfr.pot'), 'en')
        for lang in LANGUAGES:
            pofile = os.path.join(I18N_ROOT, lang, 'LC_MESSAGES', 'gouvfr.po')
            if not os.path.exists(pofile):
                ctx.run('python setup.py init_catalog -l {}'.format(lang))
                set_po_metadata(pofile, lang)
            elif update:
                ctx.run('python setup.py update_catalog -l {}'.format(lang))
                set_po_metadata(pofile, lang)

    # Front translations
    info('Extract vue translations')
    with ctx.cd(ROOT):
        ctx.run('npm run i18n:extract')
    success('Updated translations')


@task
def i18nc(ctx):
    '''Compile translations'''
    header(i18nc.__doc__)
    # Plugin translations (harvesters, views...)
    info('Compile plugin translations')
    with ctx.cd(ROOT):
        ctx.run('python setup.py compile_catalog')

    success('Compiled translations')


@task
def assets_watch(ctx):
    '''Build assets on change'''
    header(assets_watch.__doc__)
    with ctx.cd(ROOT):
        ctx.run('npm run dev', pty=True)


@task
def assets_build(ctx):
    '''Build static assets'''
    header(assets_build.__doc__)
    with ctx.cd(ROOT):
        ctx.run('npm run build', pty=True)


@task(i18nc, assets_build)
def dist(ctx, buildno=None):
    '''Package for distribution'''
    header(dist.__doc__)
    perform_dist(ctx, buildno)


@task(i18nc)
def pydist(ctx, buildno=None):
    '''Perform python packaging (without compiling assets)'''
    header(pydist.__doc__)
    perform_dist(ctx, buildno)


def perform_dist(ctx, buildno=None):
    cmd = ['python setup.py']
    if buildno:
        cmd.append('egg_info -b {0}'.format(buildno))
    cmd.append('bdist_wheel')
    with ctx.cd(ROOT):
        ctx.run(' '.join(cmd), pty=True)
    success('Distribution is available in dist directory')


@task(clean, qa, call(cover, report=True, html=True), dist, default=True)
def all(ctx):
    '''Run tests, reports and packaging'''
    pass
