from flask import current_app
from langdetect import detect
from mongoengine import signals

from udata.mongo import db

from .signals import on_new_potential_spam


class SpamMixin(object):
    """
    Mixin for models that can be checked for spam.
    Spam detection creates Report objects instead of storing spam info on the model itself.
    """

    attributes_before = None
    detect_spam_enabled: bool = True

    # These will be set during spam detection to track context
    _spam_report = None  # Reference to the created Report (if any)
    _spam_base_model = None  # Reference to the base document (for embedded docs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Save the list of texts at initialisation to not recheck for spam a text
        # if it didn't change during this request lifecycle.
        self.attributes_before = self.texts_to_check_for_spam()

    @staticmethod
    def spam_words():
        return current_app.config.get("SPAM_WORDS", [])

    @staticmethod
    def allowed_langs():
        return current_app.config.get("SPAM_ALLOWED_LANGS", [])

    @staticmethod
    def minimum_string_length_for_lang_check():
        return current_app.config.get("SPAM_MINIMUM_STRING_LENGTH_FOR_LANG_CHECK", 30)

    def clean(self):
        super().clean()

        # We do not want to check embedded document here, they will be checked
        # during the clean of their parents.
        if isinstance(self, db.Document):
            self.detect_spam()

    def save_without_spam_detection(self):
        """
        Allow to save a model without doing the spam detection (useful when saving the callbacks for exemple)
        """
        self.detect_spam_enabled = False
        self.save()
        self.detect_spam_enabled = True

    def detect_spam(self, breadcrumb=None):
        """
        This is the main function doing the spam detection.
        If spam is detected, a Report is created after the model is saved.
        """
        if not self.detect_spam_enabled:
            return

        if self.spam_is_whitelisted():
            return

        # The breadcrumb is useful during reporting to know where we came from
        # in case of a potential spam inside an embed.
        if breadcrumb is None:
            breadcrumb = []

        breadcrumb.append(self)

        for before, text in zip(self.attributes_before, self.texts_to_check_for_spam()):
            if not text:
                continue

            # We do not want to re-run the spam detection if the texts didn't change from the initialisation. If we
            # don't do this, a potential spam marked as no spam will be re-flag as soon as we make change in the model
            # (for example to set the spam status, or to add a new message). If the model is new, the texts haven't
            # changed since the init, but we still want to do the spam check.
            if before == text and not self.is_new():
                continue

            for word in SpamMixin.spam_words():
                if word in text.lower():
                    self._schedule_report(
                        text=text, breadcrumb=breadcrumb, reason=f'contains spam words "{word}"'
                    )
                    return

            # Language detection is not working well with texts of a few words.
            if (
                SpamMixin.allowed_langs()
                and len(text) > SpamMixin.minimum_string_length_for_lang_check()
            ):
                lang = detect(text.lower())
                if lang not in SpamMixin.allowed_langs():
                    self._schedule_report(
                        text=text, breadcrumb=breadcrumb, reason=f'not allowed language "{lang}"'
                    )
                    return

        for embed in self.embeds_to_check_for_spam():
            # We need to copy to avoid adding multiple time (in each loop iteration) a new element to the shared
            # breadcrumb list
            embed.detect_spam(breadcrumb.copy())

    def is_new(self):
        """
        Check if the model is new (not already saved inside DB), in this case
        we want to check for spam on all the fields.
        On subsequent requests we want to check only the modified fields.
        """
        if isinstance(self, db.Document) or isinstance(self, db.EmbeddedDocument):
            return self._created
        else:
            raise RuntimeError("SpamMixin should be a Document or an EmbeddedDocument")

    def is_spam(self, base_model=None):
        """
        Check if this model has an unhandled auto-spam report.
        For embedded documents, base_model must be provided (or cached from spam detection).
        """
        return self.get_spam_report(base_model) is not None

    def get_spam_report(self, base_model=None):
        """
        Get the unhandled auto-spam report for this model.
        For embedded documents, base_model must be provided (or cached from spam detection).
        """
        from udata.core.reports.models import Report

        if isinstance(self, db.Document):
            return Report.get_auto_spam_report(self)
        elif isinstance(self, db.EmbeddedDocument):
            if base_model is None:
                base_model = self._spam_base_model
            if base_model is None:
                raise ValueError("base_model is required for embedded documents")
            subject_path = self._get_subject_path(base_model)
            return Report.get_auto_spam_report(base_model, subject_path)
        return None

    def _get_subject_path(self, base_model):
        """
        Get the subject_path for this embedded document within base_model.
        Must be implemented by subclasses that are embedded documents.
        """
        raise NotImplementedError(
            "Embedded documents must implement _get_subject_path to generate the path "
            "within the parent document (e.g., 'discussion.2' for a Message)."
        )

    def texts_to_check_for_spam(self):
        raise NotImplementedError(
            "Please implement the `texts_to_check_for_spam` method. Should return a list of strings to check."
        )

    def embeds_to_check_for_spam(self):
        return []

    def spam_is_whitelisted(self) -> bool:
        return False

    def spam_report_message(self, breadcrumb):
        return f"Spam potentiel sur {type(self).__name__}"

    def _schedule_report(self, text, breadcrumb, reason):
        """
        Schedule a Report to be created after the model is saved.
        We need to wait for save because we need the model's ID.
        """
        base_model = breadcrumb[0]
        spam_model = self

        # Store reference to base_model for embedded documents
        if isinstance(self, db.EmbeddedDocument):
            self._spam_base_model = base_model

        def create_report_after_save(sender, document, **kwargs):
            # Only process if this is our base_model being saved
            if document != base_model:
                return

            from udata.core.reports.constants import REASON_AUTO_SPAM
            from udata.core.reports.models import Report

            # Compute subject_path for embedded documents
            subject_path = None
            if spam_model != base_model:
                try:
                    subject_path = spam_model._get_subject_path(base_model)
                except NotImplementedError:
                    pass

            # Check if report already exists to avoid duplicates
            existing = Report.get_auto_spam_report(base_model, subject_path)
            if existing:
                signals.post_save.disconnect(create_report_after_save)
                return

            # Create the Report
            message = spam_model.spam_report_message(breadcrumb)
            report = Report(
                subject=base_model,
                subject_path=subject_path,
                reason=REASON_AUTO_SPAM,
                message=f"{message}\n\nReason: {reason}\nText: {text[:500]}",
            )
            report.save()

            # Store reference to the report
            spam_model._spam_report = report

            # Emit signal for notifications
            on_new_potential_spam.send(spam_model, message=message, text=text, reason=reason)

            # Disconnect to avoid memory leaks
            signals.post_save.disconnect(create_report_after_save)

        # Connect signal - use weak=False to prevent garbage collection
        signals.post_save.connect(create_report_after_save, sender=base_model.__class__, weak=False)


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

            # Check if there's a spam report for this model
            if model_to_check.is_spam(base_model if model_to_check != base_model else None):
                # Get the report and save the callback to it
                report = model_to_check.get_spam_report(
                    base_model if model_to_check != base_model else None
                )
                if report:
                    report.callbacks[f.__name__] = {"args": args[1:], "kwargs": kwargs}
                    report.save()
            else:
                f(*args, **kwargs)

        return protected_function

    return decorator
