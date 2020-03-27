from blinker import Namespace

namespace = Namespace()

#: Trigerred when a site's metrics job is done.
on_site_metrics = namespace.signal('on-site-metrics')