from udata.core.dataservices.models import Dataservice

from .models import Dataset


@Dataservice.on_create.connect
@Dataservice.on_update.connect
@Dataservice.on_delete.connect
def update_dataset_dataservices_metric(dataservice, **kwargs):
    previous = kwargs.get("previous")
    if previous and previous.get("datasets"):
        datasets_delta = set(dat.id for dat in dataservice.datasets).symmetric_difference(
            set(dat.id for dat in previous["datasets"])
        )
    else:
        datasets_delta = set(dat.id for dat in dataservice.datasets)
    for dataset in datasets_delta:
        Dataset.get(dataset).count_dataservices()
