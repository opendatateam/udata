from udata.models import Reuse


@Reuse.on_create.connect
@Reuse.on_update.connect
def update_reuses_dataset_metric(reuse, **kwargs):
    reuse.count_datasets()
