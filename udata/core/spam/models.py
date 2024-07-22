from flask import current_app
from langdetect import detect
from mongoengine import signals

from udata.mongo import db

from .constants import NO_SPAM, NOT_CHECKED, POTENTIAL_SPAM, SPAM_STATUS_CHOICES
from .signals import on_new_potential_spam


class SpamInfo(db.EmbeddedDocument):
    status = db.StringField(choices=SPAM_STATUS_CHOICES, default=NOT_CHECKED)
    callbacks = db.DictField(default={})


class SpamMixin(object):
    spam = db.EmbeddedDocumentField(SpamInfo)

    attributes_before = None
    detect_spam_enabled: bool = True

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
        This function set a flag POTENTIAL_SPAM if a model is suspicious.
        """
        if not self.detect_spam_enabled:
            return

        # During initialisation some models can have no spam associated
        if not self.spam:
            self.spam = SpamInfo(status=NOT_CHECKED, callbacks={})

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
                    self.spam.status = POTENTIAL_SPAM
                    self._report(
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
                    self.spam.status = POTENTIAL_SPAM
                    self._report(
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

    def mark_as_no_spam(self, base_model):
        """
        When an admin mark a model as a false positive (not a real spam)
        we need to call back the saved callbacks that where delayed in `spam_protected`
        """
        callbacks = self.spam.callbacks
        self.spam.status = NO_SPAM
        self.spam.callbacks = {}
        base_model.save()

        for name, args in callbacks.items():
            callback = getattr(base_model, name)
            callback(*args["args"], **args["kwargs"])

    def is_spam(self):
        return self.spam and self.spam.status == POTENTIAL_SPAM

    def texts_to_check_for_spam(self):
        raise NotImplementedError(
            "Please implement the `texts_to_check_for_spam` method. Should return a list of strings to check."
        )

    def embeds_to_check_for_spam(self):
        return []

    def spam_is_whitelisted(self) -> bool:
        return False

    def spam_report_message(self):
        return f"Spam potentiel sur {type(self).__name__}"

    def _report(self, text, breadcrumb, reason):
        base_model = breadcrumb[0]

        def report_after_save(sender, document, **kwargs):
            # Here we early out to prevent multiple reports if multiple
            # spam are sent at the same time. Not sure if it's necessary.
            if document != base_model:
                return

            message = self.spam_report_message(breadcrumb)

            on_new_potential_spam.send(self, message=message, text=text, reason=reason)

            # We clean the listener here. Not sure if it's necessary either.
            signals.post_save.disconnect(report_after_save)

        # For `spam_report_message` we often need the ID of the document so we
        # must report after saving to have the ID available.
        # By default the signal is weak so it is dropped at the end of this function and it's
        # never called. We disconnect the signal in `report_after_save` to avoid leaks.
        signals.post_save.connect(report_after_save, sender=base_model.__class__, weak=False)


def spam_protected(get_model_to_check=None):
    """
    This decorator prevent the calling of a class method if the object is a POTENTIAL_SPAM.
    It will save the class method called with its arguments inside the `SpamInfo` object to be
    called later if needed (in case of false positive).
    The decorator accept an argument, a function to get the model to check when we are doing an operation
    on an embed document. The class method should always take a `self` as a first argument which is the base
    model to allow saving the callbacks back into Mongo (we cannot .save() an embed document).
    """

    def decorator(f):
        def protected_function(*args, **kwargs):
            base_model = args[0]
            if get_model_to_check:
                model_to_check = get_model_to_check(*args, **kwargs)
            else:
                model_to_check = base_model

            if not isinstance(model_to_check, SpamMixin):
                raise ValueError(
                    "@spam_protected should be called within a SpamMixin. "
                    + type(model_to_check).__name__
                    + " given."
                )

            if model_to_check.is_spam():
                model_to_check.spam.callbacks[f.__name__] = {"args": args[1:], "kwargs": kwargs}
                base_model.save_without_spam_detection()
            else:
                f(*args, **kwargs)

        return protected_function

    return decorator
