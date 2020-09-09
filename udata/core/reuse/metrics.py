from udata.models import Reuse


@Reuse.on_update.connect
def update_dataset_reuses_metric(reuse, **kwargs):
    reuse.count_datasets()
