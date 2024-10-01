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

    # Datasets with use_labels=false are the one that were most surely impacted by the URL modifications
    datasets = Dataset.objects(resources__url__contains="use_labels=false")

    log.info("Starting")
    log.info(f"{datasets.count()} datasets to process...")
    for dat in datasets:
        for res_format in ["csv", "xlsx"]:
            resources = [res for res in dat.resources if f"/exports/{res_format}" in res.url]
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
                    if res.url.endswith(f"/exports/{res_format}")
                    and res.title.endswith(f".{res_format}")
                )
                res_label_false = next(
                    res for res in resources if res.url.endswith("?use_labels=false")
                )
                res_label_true = next(
                    res for res in resources if res.url.endswith("?use_labels=true")
                )

                # Resource that exists prior to ODS to DCAT migration, cf https://github.com/opendatateam/udata-ods/pull/247
                # and somehow did not get migrated properly
                res_old_school = next(
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

            # We want to keep the original resource and update its URL
            # and remove all the other duplicates
            res_original.url += "?use_labels=true"
            dat.remove_resource(res_label_false)
            dat.remove_resource(res_label_true)
            if res_old_school:
                dat.remove_resource(res_old_school)

        try:
            dat.save()
            count += 1
        except ValidationError:
            log.info(f"Could not save dataset {dat.id}")
            log.info(traceback.format_exc())
            errors += 1

    log.info("Done !")
    log.info(f"Updated {count} datasets. Failed on {errors} objects.")
