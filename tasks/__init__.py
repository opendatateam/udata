import itertools
import json
import os
import re
from datetime import datetime
from glob import iglob
from os.path import exists, join
from sys import exit

from babel.messages.pofile import read_po, write_po
from babel.util import LOCALTZ
from invoke import task

from .helpers import ROOT, cyan, header, info, success

I18N_DOMAIN = "udata"


@task
def clean(ctx, node=False, translations=False, all=False):
    """Cleanup all build artifacts"""
    header("Clean all build artifacts")
    patterns = [
        "build",
        "dist",
        "cover",
        "docs/_build",
        "**/*.pyc",
        "*.egg-info",
        ".tox",
        "udata/static/*",
    ]
    if node or all:
        patterns.append("node_modules")
    if translations or all:
        patterns.append("udata/translations/*/LC_MESSAGES/udata.mo")
    for pattern in patterns:
        info(pattern)
    with ctx.cd(ROOT):
        ctx.run("rm -rf {0}".format(" ".join(patterns)))


@task
def update(ctx, migrate=False):
    """Perform a development update"""
    msg = "Update all dependencies"
    if migrate:
        msg += " and migrate data"
    header(msg)
    info("Updating Python dependencies")
    with ctx.cd(ROOT):
        ctx.run("pi3 install -e .")
        ctx.run("pip install -r requirements/develop.pip")
        info("Updating JavaScript dependencies")
        ctx.run("npm install")
        if migrate:
            info("Migrating database")
            ctx.run("udata db migrate")


@task
def i18n(ctx, update=False):
    """Extract translatable strings"""
    header("Extract translatable strings")

    info("Extract Python strings")
    with ctx.cd(ROOT):
        ctx.run("python setup.py extract_messages")

    # Fix crowdin requiring Language with `2-digit` iso code in potfile
    # to produce 2-digit iso code pofile
    # Opening the catalog also allows to set extra metadata
    potfile = join(ROOT, "udata", "translations", "{}.pot".format(I18N_DOMAIN))
    with open(potfile, "rb") as infile:
        catalog = read_po(infile, "en")
    catalog.copyright_holder = "Open Data Team"
    catalog.msgid_bugs_address = "i18n@opendata.team"
    catalog.language_team = "Open Data Team <i18n@opendata.team>"
    catalog.last_translator = "Open Data Team <i18n@opendata.team>"
    catalog.revision_date = datetime.now(LOCALTZ)
    with open(potfile, "wb") as outfile:
        write_po(outfile, catalog, width=80)

    if update:
        with ctx.cd(ROOT):
            ctx.run("python setup.py update_catalog")

    info("Extract JavaScript strings")
    keys = set()
    catalog = {}
    catalog_filename = join(ROOT, "js", "locales", "{}.en.json".format(I18N_DOMAIN))
    if exists(catalog_filename):
        with open(catalog_filename) as f:
            catalog = json.load(f)

    globs = "*.js", "*.vue", "*.hbs"
    regexps = [
        re.compile(r'(?:|\.|\s|\{)_\(\s*(?:"|\')(.*?)(?:"|\')\s*(?:\)|,)'),  # JS _('trad')
        re.compile(r'v-i18n="(.*?)"'),  # Vue.js directive v-i18n="trad"
        re.compile(r'"\{\{\{?\s*\'(.*?)\'\s*\|\s*i18n\}\}\}?"'),  # Vue.js filter {{ 'trad'|i18n }}
        re.compile(r'{{_\s*"(.*?)"\s*}}'),  # Handlebars {{_ "trad" }}
        re.compile(r"{{_\s*\'(.*?)\'\s*}}"),  # Handlebars {{_ 'trad' }}
        re.compile(r'\:[a-z0-9_\-]+="\s*_\(\'(.*?)\'\)\s*"'),  # Vue.js binding :prop="_('trad')"
    ]

    for directory, _, _ in os.walk(join(ROOT, "js")):
        glob_patterns = (iglob(join(directory, g)) for g in globs)
        for filename in itertools.chain(*glob_patterns):
            print("Extracting messages from {0}".format(cyan(filename)))
            content = open(filename).read()
            for regexp in regexps:
                for match in regexp.finditer(content):
                    key = match.group(1)
                    key = key.replace("\\n", "\n")
                    keys.add(key)
                    if key not in catalog:
                        catalog[key] = key

    # Remove old/not found translations
    for key in list(catalog.keys()):
        if key not in keys:
            del catalog[key]

    with open(catalog_filename, "w") as f:
        json.dump(catalog, f, sort_keys=True, indent=4, ensure_ascii=False, separators=(",", ": "))


@task
def i18nc(ctx):
    """Compile translations"""
    header("Compiling translations")
    with ctx.cd(ROOT):
        ctx.run("python setup.py compile_catalog")


@task(i18nc)
def test(ctx, fast=False, report=False, verbose=False, ci=False):
    """Run tests suite"""
    header("Run tests suite")
    cmd = ["pytest udata"]
    if ci:
        cmd.append("-p no:sugar --color=yes")
    if verbose:
        cmd.append("-v")
    if fast:
        cmd.append("-x")
    if report:
        cmd.append("--junitxml=reports/python/tests.xml")
    with ctx.cd(ROOT):
        ctx.run(" ".join(cmd), pty=True)


@task
def cover(ctx, html=False):
    """Run tests suite with coverage"""
    header("Run tests suite with coverage")
    cmd = "pytest --cov udata --cov-report term"
    if html:
        cmd = " ".join((cmd, "--cov-report html:reports/python/cover"))
    with ctx.cd(ROOT):
        ctx.run(cmd, pty=True)


@task
def jstest(ctx, watch=False):
    """Run Karma tests suite"""
    header("Run Karma/Mocha test suite")
    cmd = "npm run -s test:{0}".format("watch" if watch else "unit")
    with ctx.cd(ROOT):
        ctx.run(cmd)


@task
def doc(ctx):
    """Build the documentation"""
    header("Building documentation")
    with ctx.cd(ROOT):
        ctx.run("mkdocs serve", pty=True)


@task
def qa(ctx):
    """Run a quality report"""
    header("Performing static analysis")
    info("Python static analysis")
    with ctx.cd(ROOT):
        flake8_results = ctx.run("flake8 udata --jobs 1", pty=True, warn=True)
    info("JavaScript static analysis")
    with ctx.cd(ROOT):
        eslint_results = ctx.run("npm -s run lint", pty=True, warn=True)
    if flake8_results.failed or eslint_results.failed:
        exit(flake8_results.return_code or eslint_results.return_code)
    success("OK")


@task
def serve(ctx, host="localhost", port="7000"):
    """Run a development server"""
    with ctx.cd(ROOT):
        ctx.run(f"python manage.py serve -d -r -h {host} -p {port}")


@task
def work(ctx, loglevel="info"):
    """Run a development worker"""
    ctx.run("celery -A udata.worker worker --purge -l %s" % loglevel, pty=True)


@task
def beat(ctx, loglevel="info"):
    """Run celery beat process"""
    ctx.run("celery -A udata.worker beat -l %s" % loglevel)


@task
def assets_build(ctx):
    """Install and compile assets"""
    header("Building static assets")
    with ctx.cd(ROOT):
        ctx.run("npm run assets:build", pty=True)


@task
def widgets_build(ctx):
    """Compile and minify widgets"""
    header("Building widgets")
    with ctx.cd(ROOT):
        ctx.run("npm run widgets:build", pty=True)


@task
def oembed_build(ctx):
    """Compile and minify OEmbed assets"""
    header("Building OEmbed assets")
    with ctx.cd(ROOT):
        ctx.run("npm run oembed:build", pty=True)


@task
def assets_watch(ctx):
    """Build assets on change"""
    with ctx.cd(ROOT):
        ctx.run("npm run assets:watch", pty=True)


@task
def widgets_watch(ctx):
    """Build widgets on changes"""
    with ctx.cd(ROOT):
        ctx.run("npm run widgets:watch", pty=True)


@task
def oembed_watch(ctx):
    """Build OEmbed assets on changes"""
    with ctx.cd(ROOT):
        ctx.run("npm run oembed:watch", pty=True)


@task(clean, i18nc, assets_build, widgets_build, oembed_build, default=True)
def dist(ctx, buildno=None):
    """Package for distribution"""
    perform_dist(ctx, buildno)


@task(i18nc)
def pydist(ctx, buildno=None):
    """Perform python packaging (without compiling assets)"""
    perform_dist(ctx, buildno)


def perform_dist(ctx, buildno=None):
    header("Building a distribuable package")
    cmd = ["python setup.py"]
    if buildno:
        cmd.append("egg_info -b {0}".format(buildno))
    cmd.append("bdist_wheel")
    with ctx.cd(ROOT):
        ctx.run(" ".join(cmd), pty=True)
        ctx.run("twine check dist/*")
    success("Distribution is available in dist directory")
