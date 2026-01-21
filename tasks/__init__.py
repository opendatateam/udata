from datetime import datetime
from os.path import join
from sys import exit

from babel.messages.pofile import read_po, write_po
from babel.util import LOCALTZ
from invoke import task

from .helpers import ROOT, header, info, success

I18N_DOMAIN = "udata"


@task
def clean(ctx, translations=False):
    """Cleanup all build artifacts"""
    header("Clean all build artifacts")
    patterns = [
        "build",
        "dist",
        "cover",
        "docs/_build",
        "**/*.pyc",
        "*.egg-info",
    ]
    if translations:
        patterns.append("udata/translations/*/LC_MESSAGES/udata.mo")
    for pattern in patterns:
        info(pattern)
    with ctx.cd(ROOT):
        ctx.run("rm -rf {0}".format(" ".join(patterns)))


@task
def update(ctx):
    """Perform a development update"""
    msg = "Update all dependencies"
    header(msg)
    info("Updating Python dependencies")
    with ctx.cd(ROOT):
        ctx.run('pip install -e ".[dev]"')
    info("Note: Dependencies are now managed in pyproject.toml")


@task
def i18n(ctx, update=False):
    """Extract translatable strings"""
    header("Extract translatable strings")

    info("Extract Python strings")
    with ctx.cd(ROOT):
        ctx.run(
            "pybabel extract -F babel.cfg -k _ -k N_:1,2 -k P_:1c,2 -k L_ -k gettext -k ngettext:1,2 -k pgettext:1c,2 -k npgettext:1c,2,3 -k lazy_gettext -k lazy_pgettext:1c,2 --add-comments=TRANSLATORS: --width=80 -o udata/translations/udata.pot udata"
        )

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
            ctx.run(
                "pybabel update --no-fuzzy-matching -D udata -d udata/translations -i udata/translations/udata.pot"
            )


@task
def i18nc(ctx):
    """Compile translations"""
    header("Compiling translations")
    with ctx.cd(ROOT):
        ctx.run("pybabel compile -D udata -d udata/translations")


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
    if flake8_results.failed:
        exit(flake8_results.return_code)
    success("OK")


@task
def serve(ctx, host="localhost", port="7000"):
    """Run a development server"""
    with ctx.cd(ROOT):
        ctx.run(f"python manage.py serve -d -r -h {host} -p {port}", pty=True)


@task
def work(ctx, loglevel="info"):
    """Run a development worker"""
    ctx.run("celery -A udata.worker worker --purge -l %s" % loglevel, pty=True)


@task
def beat(ctx, loglevel="info"):
    """Run celery beat process"""
    ctx.run("celery -A udata.worker beat -l %s" % loglevel)


@task(clean, i18nc, default=True)
def dist(ctx):
    """Package for distribution"""
    perform_dist(ctx)


@task(i18nc)
def pydist(ctx):
    """Perform python packaging (without compiling assets)"""
    perform_dist(ctx)


def perform_dist(ctx):
    header("Building a distribuable package")
    ctx.run("uv build --wheel")
    success("Distribution is available in dist directory")
