from flask_restx.marshalling import marshal

from udata.api.versioning import version_transform
from udata.core.dataset.api_fields import dataset_fields


@version_transform(
    "Reuse",
    before="16.3.0",
    description="The datasets field returns an href link instead of the full inline list.",
)
def reuse_datasets_to_inline(data, reuse, context):
    datasets = marshal(list(reuse.datasets), dataset_fields)
    if context == "page":
        allowed = ("id", "title", "uri", "page")
        datasets = [{k: d[k] for k in allowed if k in d} for d in datasets]
    data["datasets"] = datasets
