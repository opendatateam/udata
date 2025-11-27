import pytest

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailMessage, ParagraphWithLinks, send_mail
from udata.tests.api import APITestCase
from udata.tests.helpers import capture_mails


class MailGenerationTest(APITestCase):
    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_simple_mail(self):
        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org"),
                MailMessage(_("Unknown"), paragraphs=[_("Some text")]),
            )

        assert len(mails) == 1
        assert len(mails[0].recipients) == 1
        assert mails[0].recipients[0] == "jane@example.org"
        assert mails[0].subject == "Unknown"
        assert "Some text" in mails[0].body
        assert "Some text" in mails[0].html

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_allow_none_in_paragraphs(self):
        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org"),
                MailMessage(_("Unknown"), paragraphs=[_("Some text"), None]),
            )

        assert len(mails) == 1

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_multiple_recipients(self):
        with capture_mails() as mails:
            send_mail(
                [
                    UserFactory(email="jane@example.org"),
                    UserFactory(email="john@example.org", prefered_language="fr"),
                ],
                MailMessage(_("Unknown"), paragraphs=[_("Some text")]),
            )

        assert len(mails) == 2
        assert len(mails[0].recipients) == 1
        assert mails[0].recipients[0] == "jane@example.org"
        assert mails[0].subject == "Unknown"
        assert len(mails[1].recipients) == 1
        assert mails[1].recipients[0] == "john@example.org"
        assert mails[1].subject == "Inconnu"

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_use_user_language(self):
        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org", prefered_language="fr"),
                MailMessage(_("Unknown"), paragraphs=[_("Some text")]),
            )

        assert len(mails) == 1
        assert mails[0].subject == "Inconnu"

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_use_objects_in_translations(self):
        org = OrganizationFactory(name="My Org")

        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org", prefered_language="fr"),
                MailMessage(
                    _("Unknown"),
                    paragraphs=[ParagraphWithLinks(_("Some text %(org)s", org=org))],
                ),
            )

        assert len(mails) == 1
        assert "My Org" in mails[0].body
        assert org.url_for() not in mails[0].body
        assert "My Org" in mails[0].html
        assert "<a" in mails[0].html
        assert org.url_for() in mails[0].html

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_labelled_bloc(self):
        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org", prefered_language="fr"),
                MailMessage(
                    _("Unknown"),
                    paragraphs=[LabelledContent(_("Some text:"), "Some content", inline=True)],
                ),
            )

        assert len(mails) == 1
        assert "<strong>Du texte :</strong> Some content" in mails[0].html
        assert "Du texte : Some content" in mails[0].body

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_labelled_bloc_truncation(self):
        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org", prefered_language="fr"),
                MailMessage(
                    _("Unknown"),
                    paragraphs=[
                        LabelledContent(
                            _("Some text:"),
                            """
                                Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book.
                            """,
                        )
                    ],
                ),
            )

        assert len(mails) == 1
        assert "a type specimen book." not in mails[0].html
        assert "a type specimen book." not in mails[0].body

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_escape_user_content_in_content(self):
        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org", prefered_language="fr"),
                MailMessage(
                    _("Unknown"),
                    paragraphs=[
                        LabelledContent(
                            _("Some text:"), "<script>Some content</script>", inline=True
                        )
                    ],
                ),
            )

        assert len(mails) == 1
        assert "<script>" not in mails[0].html

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_escape_user_content_in_object_label(self):
        org = OrganizationFactory(name="<script>My Org</script>")

        with capture_mails() as mails:
            send_mail(
                UserFactory(email="jane@example.org", prefered_language="fr"),
                MailMessage(
                    _("Unknown"),
                    paragraphs=[ParagraphWithLinks(_("Some text %(org)s", org=org))],
                ),
            )

        assert len(mails) == 1
        assert "<script>" not in mails[0].html
