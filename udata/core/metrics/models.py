from datetime import date, timedelta

from udata.models import db


__all__ = ('WithMetrics',)


class WithMetrics(object):
    metrics = db.DictField()

    __metrics_keys__ = []

    def get_metrics(self):
        print('IN THE GET METRICS')
        return {key:self.metrics.get(key, 0) for key in self.__metrics_keys__}

