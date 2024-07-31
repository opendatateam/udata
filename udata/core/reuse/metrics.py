from udata.models import Reuse


@Reuse.on_create.connect
@Reuse.on_update.connect
def update_reuses_dataset_metric(reuse: Reuse, **kwargs) -> None:
    reuse.count_datasets()
