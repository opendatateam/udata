"""
Remove duplicate OpenDataSoft resources
The duplicate are due to ODS modifying the URL of their CSV and XLSX exports,
the URL being the identifier of the resources in DCAT harvesting.
The default /export/csv had been existing since harvesting ODS with DCAT.
2024-08-07 : `use_labels=false` appended at the end of the URL -> first duplicates
2024-08-09 : replaced by `use_labels=true` -> second set of duplicates
"""

import logging
import traceback

from mongoengine.errors import ValidationError

from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    count = 0
    errors = 0

    original = "/exports/{0}"
    first_duplication = "?use_labels=false"
    second_duplication = "?use_labels=true"

    # Datasets with use_labels=false are the one that were most surely impacted by the URL modifications
    datasets = Dataset.objects(resources__url__contains=first_duplication)

    log.info("Starting")
    log.info(f"{datasets.count()} datasets to process...")
    for dat in datasets:
        to_save = False
        for res_format in ["csv", "xlsx"]:
            resources = [res for res in dat.resources if original.format(res_format) in res.url]
            if not resources:
                # This dataset doesn't have csv or xlsx resources
                continue
            if len(resources) not in [3, 4]:
                log.info(
                    f"Skipping, {len(resources)} {res_format} duplicate resources found for {dat.id}. We're expecting 3 or 4"
                )
                continue
            try:
                res_original = next(
                    res
                    for res in resources
                    if res.url.endswith(original.format(res_format))
                    and res.title.endswith(f".{res_format}")
                )
                res_first_duplication = next(
                    res for res in resources if res.url.endswith(first_duplication)
                )
                res_second_duplication = next(
                    res for res in resources if res.url.endswith(second_duplication)
                )

                # Resource that exists prior to ODS to DCAT migration and somehow did not get migrated properly
                # cf https://github.com/opendatateam/udata-ods/pull/247
                res_migration_duplicate = next(
                    (
                        res
                        for res in resources
                        if res.title == f"Export au format {res_format.upper()}"
                    ),
                    None,
                )

            except StopIteration:
                log.info(
                    f"Could not find expected params on {res_format} for {dat.id} : {set(res.url.split('/')[-1] for res in resources)}"
                )
                errors += 1
                continue

            # Keep the original resource and update its URL
            res_original.url += second_duplication
            # Remove all the other duplicates
            dat.remove_resource(res_first_duplication)
            dat.remove_resource(res_second_duplication)
            if res_migration_duplicate:
                dat.remove_resource(res_migration_duplicate)

            to_save = True

        if to_save:
            try:
                dat.save()
                count += 1
            except ValidationError:
                log.info(f"Could not save dataset {dat.id}")
                log.info(traceback.format_exc())
                errors += 1

    log.info("Done !")
    log.info(f"Updated {count} datasets. Failed on {errors} objects.")
