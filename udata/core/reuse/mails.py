from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage, ParagraphWithLinks


def new_reuse(reuse: Reuse, dataset: Dataset) -> MailMessage:
    return MailMessage(
        subject=_("New reuse on your dataset"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "A new reuse has been published by %(user_or_org)s on your dataset %(dataset)s",
                    user_or_org=reuse.organization or reuse.owner,
                    dataset=dataset,
                )
            ),
            LabelledContent(_("Reuse title:"), str(reuse.title)),
            MailCTA(_("View the reuse"), reuse.url_for()),
        ],
    )
