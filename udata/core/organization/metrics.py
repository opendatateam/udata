from udata.models import Dataset, Reuse


@Dataset.on_create.connect
@Dataset.on_update.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    print("----------------------------------------------------------------------")
    print("IN DATASET FOR ORGANIZATION METRIC UPDATE")
    print(document)
    if document.organization:
        document.organization.count_datasets()
    print(document.organization.get_metrics)
    print("----------------------------------------------------------------------")


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    print("----------------------------------------------------------------------")
    print("IN REUSE FOR ORGANIZATION METRIC UPDATE")
    print(document)
    if document.organization:
        document.organization.count_reuses()
    print(document.organization.get_metrics)
    print("----------------------------------------------------------------------")