from udata.api_fields import field
from udata.mongo import db

__all__ = ("WithMetrics",)


class WithMetrics(object):
    metrics = field(
        db.DictField(),
        readonly=True,
        auditable=False,
    )

    __metrics_keys__ = []

    def get_metrics(self):
        return {key: self.metrics.get(key, 0) for key in self.__metrics_keys__}
