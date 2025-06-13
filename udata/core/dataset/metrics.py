from udata.core.dataservices.models import Dataservice

from .models import Dataset


@Dataservice.on_create.connect
@Dataservice.on_update.connect
@Dataservice.on_delete.connect
def update_dataset_dataservices_metric(dataservice, **kwargs):
    for dataset in dataservice.datasets:
        # dataset is a LazyReferenceField
        Dataset.get(dataset.pk).count_dataservices()
