from udata.core.reuse.models import Reuse

from .models import Dataservice


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_dataservice_reuses_metric(reuse, **kwargs):
    previous = kwargs.get("previous")
    if previous and previous.get("dataservices"):
        dataservices_delta = set(ds.id for ds in reuse.dataservices).symmetric_difference(
            set(ds.id for ds in previous["dataservices"])
        )
    else:
        dataservices_delta = set(ds.id for ds in reuse.dataservices)
    for dataservice_id in dataservices_delta:
        dataservice = Dataservice.objects(id=dataservice_id).first()
        if dataservice:
            dataservice.count_reuses()
