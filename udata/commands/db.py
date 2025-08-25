import collections
import copy
import logging
import os
import sys
import traceback
from itertools import groupby
from typing import Optional
from uuid import uuid4

import click
import mongoengine
from bson import DBRef

from udata import migrations
from udata.commands import cli, cyan, echo, green, magenta, red, white, yellow
from udata.core.dataset.models import Dataset, Resource
from udata.mongo.document import get_all_models

# Date format used to for display
DATE_FORMAT = "%Y-%m-%d %H:%M"

log = logging.getLogger(__name__)


@cli.group("db")
def grp():
    """Database related operations"""
    pass


def log_status(migration, status):
    """Properly display a migration status line"""
    name = os.path.splitext(migration.filename)[0]
    display = ":".join((migration.plugin, name)) + " "
    log.info("%s [%s]", "{:.<70}".format(display), status)


def status_label(record):
    if record.ok:
        return green(record.last_date.strftime(DATE_FORMAT))
    elif not record.exists():
        return yellow("Not applied")
    else:
        return red(record.status)


def format_output(output, success=True, traceback=None):
    echo("  │")
    for level, msg in output:
        echo("  │ {0}".format(msg))
    echo("  │")
    if traceback:
        for tb in traceback.split("\n"):
            echo("  │ {0}".format(tb))
    echo("  │")
    echo("  └──[{0}]".format(green("OK") if success else red("KO")))
    echo("")


@grp.command()
def status():
    """Display the database migrations status"""
    for migration in migrations.list_available():
        log_status(migration, status_label(migration.record))


@grp.command()
@click.option("-r", "--record", is_flag=True, help="Only records the migrations")
@click.option("-d", "--dry-run", is_flag=True, help="Only print migrations to be applied")
def migrate(record, dry_run=False):
    """Perform database migrations"""
    success = True
    for migration in migrations.list_available():
        if migration.record.ok or not success:
            log_status(migration, cyan("Skipped"))
        else:
            status = magenta("Recorded") if record else yellow("Apply")
            log_status(migration, status)
            try:
                output = migration.execute(recordonly=record, dryrun=dry_run)
            except migrations.RollbackError as re:
                format_output(re.migrate_exc.output, False)
                log_status(migration, red("Rollback"))
                format_output(re.output, not re.exc)
                success = False
            except migrations.MigrationError as me:
                format_output(me.output, False, traceback=me.traceback)
                success = False
            else:
                format_output(output, True)
    return success


@grp.command()
@click.argument("plugin_or_specs")
@click.argument("filename", default=None, required=False, metavar="[FILENAME]")
def unrecord(plugin_or_specs, filename):
    """
    Remove a database migration record.

    \b
    A record can be expressed with the following syntaxes:
     - plugin filename
     - plugin filename.js
     - plugin:filename
     - plugin:fliename.js
    """
    migration = migrations.get(plugin_or_specs, filename)
    removed = migration.unrecord()
    if removed:
        log.info("Removed migration %s", migration.label)
    else:
        log.error("Migration not found %s", migration.label)


@grp.command()
@click.argument("plugin_or_specs")
@click.argument("filename", default=None, required=False, metavar="[FILENAME]")
def info(plugin_or_specs, filename):
    """
    Display detailed info about a migration
    """
    migration = migrations.get(plugin_or_specs, filename)
    log_status(migration, status_label(migration.record))
    try:
        echo(migration.module.__doc__)
    except migrations.MigrationError:
        echo(yellow("Module not found"))

    for op in migration.record.get("ops", []):
        display_op(op)


def display_op(op):
    timestamp = white(op["date"].strftime(DATE_FORMAT))
    label = white(op["type"].title()) + " "
    echo("{label:.<70} [{date}]".format(label=label, date=timestamp))
    format_output(op["output"], success=op["success"], traceback=op.get("traceback"))


def check_references(models_to_check):
    # Cannot modify local scope from Python… :-(
    class Log:
        errors = []

    def print_and_save(text: str):
        Log.errors.append(text.strip())
        print(text)

    errors = collections.defaultdict(int)

    references = []
    for model in get_all_models():
        if model.__name__ == "Activity":
            print("Skipping Activity model, scheduled for deprecation")
            continue
        if model.__name__ == "GeoLevel":
            print("Skipping GeoLevel model, scheduled for deprecation")
            continue

        if models_to_check and model.__name__ not in models_to_check:
            continue

        # find "root" ReferenceField fields
        refs = [
            elt
            for elt in model._fields.values()
            if isinstance(elt, mongoengine.fields.ReferenceField)
        ]
        references += [
            {
                "model": model,
                "repr": f"{model.__name__}.{r.name}",
                "name": r.name,
                "destination": r.document_type.__name__,
                "type": "direct",
            }
            for r in refs
        ]

        # find "root" GenericReferenceField
        refs = [
            elt
            for elt in model._fields.values()
            if isinstance(elt, mongoengine.fields.GenericReferenceField)
        ]
        references += [
            {
                "model": model,
                "repr": f"{model.__name__}.{r.name}",
                "name": r.name,
                "destination": "Generic",
                "type": "direct",
            }
            for r in refs
        ]

        # find ListField with ReferenceField
        list_fields = [
            elt for elt in model._fields.values() if isinstance(elt, mongoengine.fields.ListField)
        ]
        list_refs = [
            elt for elt in list_fields if isinstance(elt.field, mongoengine.fields.ReferenceField)
        ]
        references += [
            {
                "model": model,
                "repr": f"{model.__name__}.{lr.name}",
                "name": lr.name,
                "destination": lr.field.document_type.__name__,
                "type": "list",
            }
            for lr in list_refs
        ]

        # find ListField w/ EmbeddedDocumentField w/ ReferenceField
        list_embeds = [
            (elt, elt.field)
            for elt in list_fields
            if isinstance(elt.field, mongoengine.fields.EmbeddedDocumentField)
        ]
        for embed, embed_field in list_embeds:
            embed_refs = [
                elt
                for elt in embed_field.document_type_obj._fields.values()
                if isinstance(elt, mongoengine.fields.ReferenceField)
            ]
            references += [
                {
                    "model": model,
                    "repr": f"{model.__name__}.{embed.name}__{er.name}",
                    "name": f"{embed.name}__{er.name}",
                    "destination": er.document_type.__name__,
                    "type": "embed_list",
                }
                for er in embed_refs
            ]

        # find EmbeddedDocumentField w/ ReferenceField
        embeds = [
            elt
            for elt in model._fields.values()
            if isinstance(elt, mongoengine.fields.EmbeddedDocumentField)
        ]
        for embed_field in embeds:
            embed_refs = [
                elt
                for elt in embed_field.document_type_obj._fields.values()
                if isinstance(elt, mongoengine.fields.ReferenceField)
            ]
            references += [
                {
                    "model": model,
                    "repr": f"{model.__name__}.{embed_field.name}__{er.name}",
                    "name": f"{embed_field.name}__{er.name}",
                    "destination": er.document_type.__name__,
                    "type": "embed",
                }
                for er in embed_refs
            ]

        # find EmbeddedDocumentField w/ ListField w/ ReferenceField
        for embed_field in embeds:
            embed_lists = [
                elt
                for elt in embed_field.document_type_obj._fields.values()
                if isinstance(elt, mongoengine.fields.ListField)
            ]
            elists_refs = [
                elt
                for elt in embed_lists
                if isinstance(elt.field, mongoengine.fields.ReferenceField)
            ]
            references += [
                {
                    "model": model,
                    "repr": f"{model.__name__}.{embed_field.name}__{lr.name}",
                    "name": f"{embed_field.name}__{lr.name}",
                    "destination": lr.field.document_type.__name__,
                    "type": "embed_list_ref",
                }
                for lr in elists_refs
            ]

    print("Those references will be inspected:")
    for reference in references:
        print(f"- {reference['repr']}({reference['destination']}) — {reference['type']}")
    print("")

    total = 0
    for model, model_references in groupby(references, lambda i: i["model"]):
        model_references = list(model_references)
        count = model.objects.count()
        print(f"- doing {count} {model.__name__}…")
        errors[model] = {}

        qs = model.objects().no_cache().all()
        with click.progressbar(qs, length=count) as models:
            for obj in models:
                for reference in model_references:
                    key = f"\t- {reference['repr']}({reference['destination']}) — {reference['type']}…"
                    if key not in errors[model]:
                        errors[model][key] = 0

                    try:
                        if reference["type"] == "direct":
                            try:
                                _ = getattr(obj, reference["name"])
                            except mongoengine.errors.DoesNotExist:
                                errors[model][key] += 1
                                print_and_save(
                                    f"\t{model.__name__}#{obj.id} have a broken reference for `{reference['name']}`"
                                )
                        elif reference["type"] == "list":
                            field_exists = (
                                f"{reference['name']}__exists"  # Eg: "contact_points__exists"
                            )
                            if model.objects(id=obj.id, **{field_exists: True}).count() == 0:
                                # See https://github.com/MongoEngine/mongoengine/issues/267#issuecomment-283065318
                                # Setting it explicitely to an empty list actually removes the field, it shouldn't.
                                errors[model][key] += 1
                                print_and_save(
                                    f"\t{model.__name__}#{obj.id} have a non existing field `{reference['name']}`, instead of an empty list"
                                )
                            else:
                                attr_list = getattr(obj, reference["name"])
                                for i, sub in enumerate(attr_list):
                                    # If it's still an instance of DBRef it means that it failed to
                                    # dereference the ID.
                                    if isinstance(sub, DBRef):
                                        errors[model][key] += 1
                                        print_and_save(
                                            f"\t{model.__name__}#{obj.id} have a broken reference for {reference['name']}[{i}]"
                                        )
                        elif reference["type"] == "embed_list":
                            p1, p2 = reference["name"].split("__")
                            attr_list = getattr(obj, p1, [])
                            for i, sub in enumerate(attr_list):
                                try:
                                    getattr(sub, p2)
                                except mongoengine.errors.DoesNotExist:
                                    errors[model][key] += 1
                                    print_and_save(
                                        f"\t{model.__name__}#{obj.id} have a broken reference for {p1}[{i}].{p2}"
                                    )
                        elif reference["type"] == "embed":
                            p1, p2 = reference["name"].split("__")
                            sub = getattr(obj, p1)
                            if sub is None:
                                continue
                            try:
                                getattr(sub, p2)
                            except mongoengine.errors.DoesNotExist:
                                errors[model][key] += 1
                                print_and_save(
                                    f"\t{model.__name__}#{obj.id} have a broken reference for {p1}.{p2}"
                                )
                        elif reference["type"] == "embed_list_ref":
                            p1, p2 = reference["name"].split("__")
                            a = getattr(obj, p1)
                            if a is None:
                                continue
                            sub = getattr(a, p2, [])
                            for i, child in enumerate(sub):
                                # If it's still an instance of DBRef it means that it failed to
                                # dereference the ID.
                                if isinstance(child, DBRef):
                                    errors[model][key] += 1
                                    print_and_save(
                                        f"\t{model.__name__}#{obj.id} have a broken reference for {p1}.{p2}[{i}]"
                                    )
                        else:
                            print_and_save(f"Unknown ref type {reference['type']}")
                    except mongoengine.errors.FieldDoesNotExist:
                        print_and_save(
                            f"[ERROR for {model.__name__} {obj.id}] {traceback.format_exc()}"
                        )

        for key, nb_errors in errors[model].items():
            print(f"{key}: {nb_errors}")
            total += nb_errors

    print(f"\n Total errors: {total}")

    if total > 0:
        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                scope.set_extra("errors", Log.errors)
                sentry_sdk.capture_message(f"{total} integrity errors", "fatal")
        except ImportError:
            print("`sentry_sdk` not installed. The errors weren't reported")
        sys.exit(1)


@grp.command()
@click.option("--models", multiple=True, default=[], help="Model(s) to check")
def check_integrity(models):
    """Check the integrity of the database from a business perspective"""
    check_references(models)


@grp.command()
@click.option(
    "-sdid",
    "--skip-duplicates-inside-dataset",
    is_flag=True,
    help="Do not show duplicates inside the same dataset (same resource ID inside one dataset)",
)
@click.option(
    "-sdod",
    "--skip-duplicates-outside-dataset",
    is_flag=True,
    help="Do not show duplicates between datasets (same resource ID shared between datasets)",
)
@click.option(
    "-e",
    "--exclude-org",
    help="Exclude some org datasets",
)
@click.option(
    "-o",
    "--only-org",
    help="Only datasets from this org",
)
@click.option(
    "-f",
    "--fix",
    is_flag=True,
    help="Auto-fix some problems",
)
def check_duplicate_resources_ids(
    skip_duplicates_inside_dataset: bool,
    skip_duplicates_outside_dataset: bool,
    exclude_org: Optional[str],
    only_org: Optional[str],
    fix: bool,
):
    resources = {}
    dry_run = "[ DONE ]" if fix else "[DRYRUN]"

    def get_checksum_value(resource: Resource):
        if resource.checksum:
            return resource.checksum.value

        return resource.extras.get("analysis:checksum")

    with click.progressbar(
        Dataset.objects,
        Dataset.objects().count(),
    ) as datasets:
        for dataset in datasets:
            for resource in dataset.resources:
                if resource.id not in resources:
                    resources[resource.id] = {"resources": [], "datasets": set()}

                resources[resource.id]["resources"].append(resource)
                resources[resource.id]["datasets"].add(dataset)

    # Keep duplicated resources only
    resources = {id: info for id, info in resources.items() if len(info["resources"]) != 1}

    count_resources = 0
    count_datasets = 0
    for id, info in resources.items():
        if len(info["datasets"]) == 1 and skip_duplicates_inside_dataset:
            continue

        if len(info["datasets"]) > 1 and skip_duplicates_outside_dataset:
            continue

        # Filter out meteo france
        if (
            exclude_org
            and list(info["datasets"])[0].organization
            and str(list(info["datasets"])[0].organization.id) == exclude_org
        ):
            continue

        # Filter everything except meteo france
        if only_org and (
            not list(info["datasets"])[0].organization
            or str(list(info["datasets"])[0].organization.id) != only_org
        ):
            continue

        count = len(info["resources"])
        print(f"With ID {id}: {count} resources")
        for dataset in info["datasets"]:
            count_datasets += 1
            print(f"\t- Dataset#{dataset.id} {dataset.title}")
        print("")
        for resource in info["resources"]:
            count_resources += 1
            print(
                f"\t- Resource {resource.title} ({get_checksum_value(resource)} / {resource.url})"
            )

        print()

        if len(info["datasets"]) == 1 and len(info["resources"]) == 2:
            dataset = next(iter(info["datasets"]))

            resource1 = info["resources"][0]
            resource2 = info["resources"][1]

            new_resources = []
            highlight_ids = [id]
            if (
                get_checksum_value(resource1) == get_checksum_value(resource2)
                and resource1.url == resource2.url
            ):
                print(
                    f"{dry_run} Since checksum and URL are the same, fixing by removing the second resource…\n"
                )

                new_resources = [r for r in dataset.resources if r != resource2]
            else:
                print(
                    f"{dry_run} Since checksum and URL are not the same, fixing by setting a new ID on second resource…\n"
                )

                # Just for logging we copy the resource to avoid changing the ID
                # on the original resource (and have a clear compare at the end)
                new_resource2 = copy.deepcopy(resource2)
                new_resource2.id = uuid4()
                highlight_ids.append(new_resource2.id)

                # Replace `resource2` by `new_resource2` in the `new_resources` array.
                new_resources = [
                    (new_resource2 if r == resource2 else r) for r in dataset.resources
                ]

            print(f"{dry_run} Previous resources ({len(dataset.resources)})")
            for r in dataset.resources:
                highlight = " <---- CHANGED !" if r.id in highlight_ids else ""
                print(f"{dry_run} \t{r.id} {r.title} {highlight}")

            print(f"{dry_run} New resources ({len(new_resources)})")
            for r in new_resources:
                highlight = " <---- CHANGED !" if r.id in highlight_ids else ""
                print(f"{dry_run} \t{r.id} {r.title} {highlight}")

            if fix:
                dataset.resources = new_resources
                dataset.save()

        print()
        print("---")
        print("---")
        print("---")
        print()

    print(f"Resources with duplicated IDs: {count_resources}")
    print(f"Datasets concerned {count_datasets}")
