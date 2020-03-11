from udata.models import Reuse


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_dataset_reuses_metric(reuse, **kwargs):
    for dataset in reuse.datasets:
        dataset.count_reuses()
