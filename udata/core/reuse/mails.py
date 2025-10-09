from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage, ParagraphWithLinks


def new_reuse(reuse: Reuse, dataset: Dataset) -> MailMessage:
    return MailMessage(
        subject=_("New membership request"),
        paragraphs=[
            ParagraphWithLinks(
                _(
                    "Une nouvelle réutilisation a été publiée par %(user_or_org)s sur votre jeu de données %(dataset)s",
                    user_or_org=reuse.organization or reuse.owner,
                    dataset=dataset,
                )
            ),
            LabelledContent(_("Titre de la réutilisation :"), str(reuse.title)),
            MailCTA(_("Voir la réutilisation"), reuse.url_for()),
        ],
    )
