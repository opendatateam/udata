from flask import current_app
from langdetect import detect

from .signals import on_new_potential_spam


class SpamMixin(object):
    """
    Mixin for models that can be checked for spam.
    Spam detection creates Report objects instead of storing spam info on the model itself.

    Classes using this mixin must connect the post_save signal:
        post_save.connect(MyModel.post_save, sender=MyModel)

    Subclasses must implement `fields_to_check_for_spam()` which returns a dict
    mapping field names to their text values, e.g.: {"title": "My title", "content": "Some text"}
    """

    detect_spam_enabled: bool = True

    # Reference to the created Report (if any), set after post_save
    _spam_report = None

    @staticmethod
    def spam_words():
        return current_app.config.get("SPAM_WORDS", [])

    @staticmethod
    def allowed_langs():
        return current_app.config.get("SPAM_ALLOWED_LANGS", [])

    @staticmethod
    def minimum_string_length_for_lang_check():
        return current_app.config.get("SPAM_MINIMUM_STRING_LENGTH_FOR_LANG_CHECK", 30)

    def save_without_spam_detection(self):
        """
        Allow to save a model without doing the spam detection (useful when saving the callbacks for exemple)
        """
        self.detect_spam_enabled = False
        self.save()
        self.detect_spam_enabled = True

    def fields_to_check_for_spam(self):
        """
        Return a dict mapping field names to text values to check for spam.
        Field names should match MongoEngine field paths (e.g., "title", "discussion.0.content").
        """
        raise NotImplementedError(
            "Please implement the `fields_to_check_for_spam` method. "
            "Should return a dict like {'field_name': 'text value'}."
        )

    def embeds_to_check_for_spam(self):
        return []

    def spam_is_whitelisted(self) -> bool:
        return False

    def spam_report_message(self, breadcrumb):
        return f"Spam potentiel sur {type(self).__name__}"

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        """
        Detect spam and create Report after the document is saved.
        Must be connected via: post_save.connect(MyModel.post_save, sender=MyModel)
        """
        if not document.detect_spam_enabled:
            return

        if document.spam_is_whitelisted():
            return

        spam_info = cls._detect_spam_in_document(document, kwargs.get("created", False))
        if not spam_info:
            return

        cls._create_spam_report(document, spam_info)

    @classmethod
    def _detect_spam_in_document(cls, document, is_created, breadcrumb=None):
        """
        Detect spam in document and its embeds.
        Returns spam info dict if spam found, None otherwise.
        """
        if breadcrumb is None:
            breadcrumb = []

        breadcrumb.append(document)

        changed_fields = set(document._get_changed_fields())

        for field_name, text in document.fields_to_check_for_spam().items():
            if not text:
                continue

            # Only check fields that have changed (or all fields if document is new)
            field_changed = is_created or any(
                field_name.startswith(cf) or cf.startswith(field_name.split(".")[0])
                for cf in changed_fields
            )
            if not field_changed:
                continue

            for word in SpamMixin.spam_words():
                if word in text.lower():
                    return {
                        "spam_model": document,
                        "text": text,
                        "breadcrumb": breadcrumb,
                        "reason": f'contains spam words "{word}"',
                    }

            if (
                SpamMixin.allowed_langs()
                and len(text) > SpamMixin.minimum_string_length_for_lang_check()
            ):
                lang = detect(text.lower())
                if lang not in SpamMixin.allowed_langs():
                    return {
                        "spam_model": document,
                        "text": text,
                        "breadcrumb": breadcrumb,
                        "reason": f'not allowed language "{lang}"',
                    }

        # Check embedded documents
        for embed in document.embeds_to_check_for_spam():
            # Embeds are always "new" in the context of spam checking since we check their content
            spam_info = cls._detect_spam_in_embed(embed, breadcrumb.copy())
            if spam_info:
                return spam_info

        return None

    @classmethod
    def _detect_spam_in_embed(cls, embed, breadcrumb):
        """Detect spam in an embedded document."""
        breadcrumb.append(embed)

        for field_name, text in embed.fields_to_check_for_spam().items():
            if not text:
                continue

            for word in SpamMixin.spam_words():
                if word in text.lower():
                    return {
                        "spam_model": embed,
                        "text": text,
                        "breadcrumb": breadcrumb,
                        "reason": f'contains spam words "{word}"',
                    }

            if (
                SpamMixin.allowed_langs()
                and len(text) > SpamMixin.minimum_string_length_for_lang_check()
            ):
                lang = detect(text.lower())
                if lang not in SpamMixin.allowed_langs():
                    return {
                        "spam_model": embed,
                        "text": text,
                        "breadcrumb": breadcrumb,
                        "reason": f'not allowed language "{lang}"',
                    }

        return None

    @classmethod
    def _create_spam_report(cls, document, spam_info):
        """Create a spam Report from detected spam info."""
        from udata.core.reports.constants import REASON_AUTO_SPAM
        from udata.core.reports.models import Report

        spam_model = spam_info["spam_model"]
        text = spam_info["text"]
        breadcrumb = spam_info["breadcrumb"]
        reason = spam_info["reason"]

        subject_embed_id = None
        if spam_model != document and hasattr(spam_model, "id"):
            subject_embed_id = spam_model.id

        # Check if report already exists (pending or dismissed) to avoid duplicates
        # We don't want to re-create a report for something that was already dismissed
        existing = Report.objects(
            subject=document,
            reason=REASON_AUTO_SPAM,
            subject_embed_id=subject_embed_id,
        ).first()
        if existing:
            return

        # Create the Report
        message = spam_model.spam_report_message(breadcrumb)
        report = Report(
            subject=document,
            subject_embed_id=subject_embed_id,
            reason=REASON_AUTO_SPAM,
            message=f"{message}\n\nReason: {reason}\nText: {text[:500]}",
        )
        report.save()

        # Store reference to the report on the spam model
        spam_model._spam_report = report

        # Emit signal for notifications
        on_new_potential_spam.send(spam_model, message=message, text=text, reason=reason)


def spam_protected(get_model_to_check=None):
    """
    This decorator prevents the calling of a class method if the object is a POTENTIAL_SPAM.
    It will save the class method called with its arguments inside the Report's callbacks
    to be called later if needed (in case of false positive).

    The decorator accepts an argument, a function to get the model to check when we are doing an operation
    on an embedded document. The class method should always take a `self` as a first argument which is the base
    model to allow saving the callbacks back into the Report.
    """

    def decorator(f):
        def protected_function(*args, **kwargs):
            base_model = args[0]
            if get_model_to_check:
                model_to_check = get_model_to_check(*args, **kwargs)

                if not model_to_check:
                    f(*args, **kwargs)
                    return
            else:
                model_to_check = base_model

            if not isinstance(model_to_check, SpamMixin):
                raise ValueError(
                    "@spam_protected should be called within a SpamMixin. "
                    + type(model_to_check).__name__
                    + " given."
                )

            # Check if a spam report was created during this request
            report = model_to_check._spam_report
            if report:
                report.callbacks[f.__name__] = {"args": args[1:], "kwargs": kwargs}
                report.save()
            else:
                f(*args, **kwargs)

        return protected_function

    return decorator
