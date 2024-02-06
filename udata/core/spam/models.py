from flask import current_app
from langdetect import detect

from udata.models import db
from .signals import on_new_potential_spam

NOT_CHECKED = 'not_checked'
POTENTIAL_SPAM = 'potential_spam'
NO_SPAM = 'no_spam'

class SpamInfo(db.EmbeddedDocument):
    status = db.StringField(choices=[NOT_CHECKED, POTENTIAL_SPAM, NO_SPAM], default=NOT_CHECKED)
    callbacks = db.DictField(default={})

class SpamMixin(object):
    spam = db.EmbeddedDocumentField(SpamInfo)

    attributes_before = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attributes_before = self.attributes_to_check_for_spam()

    @staticmethod
    def spam_words():
        return current_app.config.get('SPAM_WORDS', [])
    
    @staticmethod
    def allowed_langs():
        return current_app.config.get('SPAM_ALLOWED_LANGS', [])

    def clean(self):
        super().clean()

        # We do not want to check embeded document here, they will be checked
        # during the clean of their parents.
        if isinstance(self, db.Document):
            self.detect_spam()

    def detect_spam(self, breadcrumb = None):
        """
        This is the main function doing the spam detection.
        This function set a flag POTENTIAL_SPAM if a model is suspicious.
        """
        # During initialisation some models can have no spam associated
        if not self.spam:
            self.spam = SpamInfo(status=NOT_CHECKED, callbacks={})

        # The breadcrumb is useful during reporting to know where we came from
        # in case of a potential spam inside an embed.
        if breadcrumb is None:
            breadcrumb = []

        breadcrumb.append(self)

        # We do not want to try to detect spam if we are only trying to set the
        # the spam status. If we try to detect the spam status we cannot set the
        # status as NO_SPAM because this function will change the status again
        # before saving to POTENTIAL_SPAM.
        # Note that this is working because when we manualy set a model as NO_SPAM we only
        # change these fields and nothing else.
        # But we still want to check for embed spam (a NO_SPAM discussion could contain
        # spammy messages)
        # Note that the first time a model is created `_get_changed_fields` is empty so we must
        # do the spam detection
        for before, text in zip(self.attributes_before, self.attributes_to_check_for_spam()):
            if not text:
                continue

            # We do not want to re-run the spam detection if the texts didn't changed from the initialisation.
            # If the model is new, the texts haven't changed since the init but we still we want to do the spam check.
            if before == text and not self.is_new():
                continue

            for word in SpamMixin.spam_words():
                if word in text.lower():
                    self.spam.status = POTENTIAL_SPAM
                    self._report(text=text, breadcrumb=breadcrumb, reason=f"contains spam words \"{word}\"")
                    return

            # Language detection is not working well with texts of a few words.
            if SpamMixin.allowed_langs() and len(text) > 30:
                lang = detect(text)
                if lang not in SpamMixin.allowed_langs():
                    self.spam.status = POTENTIAL_SPAM
                    self._report(text=text, breadcrumb=breadcrumb, reason=f"not allowed language \"{lang}\"")
                    return

        for embed in self.embeds_to_check_for_spam():
            # We need to copy to avoid adding multiple time (in each loop iteration) a new element to the shared breadcrumb list
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
        we need to callback the saved callbacks that where delayed in `spam_protected`
        """
        callbacks = self.spam.callbacks
        self.spam.status = NO_SPAM
        self.spam.callbacks = {}
        base_model.save()

        for name, args in callbacks.items():
            callback = getattr(base_model, name)
            callback(*args['args'], **args['kwargs'])

    def is_spam(self):
        return self.spam and self.spam.status == POTENTIAL_SPAM
    
    def attributes_to_check_for_spam(self):
        raise NotImplementedError("Please implement the `attributes_to_check_for_spam` method. Should return the list of attributes to check.")

    def embeds_to_check_for_spam(self):
        return []
    
    def spam_report_title(self):
        return type(self).__name__
    
    def spam_report_link(self):
        return None
    
    def _report(self, text, breadcrumb, reason):
        # Note that all the chain should be a SpamMixin, maybe we could filter out if it's not the case here…
        title = " → ".join(map(lambda o: o.spam_report_title(), breadcrumb))

        # Select the first link in the embed list (for exemple message doesn't have a link, so check if discussion have one)
        for object in reversed(breadcrumb):
            link = object.spam_report_link()
            if link:
                break

        on_new_potential_spam.send(self, title=title, link=link, text=text, reason=reason)


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
                raise ValueError("@spam_protected should be called within a SpamMixin. " + type(model_to_check).__name__ + " given.")

            if model_to_check.is_spam():
                model_to_check.spam.callbacks[f.__name__] = {
                    'args': args[1:],
                    'kwargs': kwargs
                }
                # At this point we recall `detect_spam`, but there is a check inside `detect_spam` to not do nothing if 
                # we only change spam.* fields.
                # Here we call save() on the base model because we cannot save an embed document.
                base_model.save()
            else:
                f(*args, **kwargs)

        return protected_function
    return decorator

