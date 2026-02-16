from mongoengine.fields import DictField

from udata.api_fields import field

__all__ = ("WithMetrics",)


class WithMetrics(object):
    metrics = field(
        DictField(),
        readonly=True,
        auditable=False,
    )

    __metrics_keys__ = []

    def get_metrics(self):
        return {key: self.metrics.get(key, 0) for key in self.__metrics_keys__}
