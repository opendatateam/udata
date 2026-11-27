from collections import OrderedDict

from udata.i18n import lazy_gettext as _

IMAGE_SIZES = [400, 100, 50]

BODY_TYPES = OrderedDict(
    [
        ("markdown", _("Markdown")),
        ("html", _("HTML")),
        ("blocs", _("Blocs")),
    ]
)

# Owned by users or organizations and rendered by external sites (eg. a vertical),
# never on the main site.
EXTERNAL_PAGE = "external_page"

POST_KINDS = OrderedDict(
    [
        ("news", _("News")),
        ("page", _("Page")),
        (EXTERNAL_PAGE, _("External page")),
    ]
)
