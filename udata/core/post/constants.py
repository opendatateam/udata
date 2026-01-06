from collections import OrderedDict

from udata.i18n import lazy_gettext as _

IMAGE_SIZES = [400, 100, 50]

BODY_TYPES = OrderedDict(
    [
        ("markdown", _("Markdown")),
        ("html", _("HTML")),
    ]
)

POST_KINDS = OrderedDict(
    [
        ("news", _("News")),
        ("page", _("Page")),
    ]
)
