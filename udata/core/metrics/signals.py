from blinker import Namespace

namespace = Namespace()

#: Trigerred when a site's metrics job is done.
on_site_metrics_computed = namespace.signal('on-site-metrics-computed')
