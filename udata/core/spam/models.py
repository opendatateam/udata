import logging
from flask import current_app
from mongoengine import signals

from udata.models import db

NOT_CHECKED = 'not_checked'
POTENTIEL_SPAM = 'potentiel_spam'
NO_SPAM = 'no_spam'

class SpamInfo(db.EmbeddedDocument):
    status = db.StringField(choices=[NOT_CHECKED, POTENTIEL_SPAM, NO_SPAM], default=NO_SPAM)
    callbacks = db.DictField(default={})

class SpamMixin(object):
    spam = db.EmbeddedDocumentField(SpamInfo)

    @staticmethod
    def spam_words():
        return current_app.config.get('SPAM_WORDS', [])

    def detect_spam_listener(sender, document):
        if not isinstance(document, SpamMixin):
            return

        document.detect_spam()

    def detect_spam(self):
        # We may use `self._get_changed_fields()` to check
        # if we didn't mark this text as valid.
        if not self.spam:
            self.spam = SpamInfo(status=NOT_CHECKED, callbacks={})

        # if self._get_changed_fields():
        #     logging.warning("inside " + type(self).__name__ + ", ".join(self._get_changed_fields()))

        if self.spam.status != NO_SPAM:
            for text in self.attributes_to_check_for_spam():
                for word in SpamMixin.spam_words():
                    if word in text:
                        self.spam.status = POTENTIEL_SPAM
                        return

        for embed in self.embeds_to_check_for_spam():
            embed.detect_spam()

    def mark_as_no_spam(self, base_model):
        callbacks = self.spam.callbacks
        self.spam.status = NO_SPAM
        self.spam.callbacks = {}
        base_model.save()

        for name, args in callbacks.items():
            callback = getattr(base_model, name)
            callback(*args['args'], **args['kwargs'])

    def is_spam(self):
        return self.spam and self.spam.status == POTENTIEL_SPAM
    
    def attributes_to_check_for_spam(self):
        raise NotImplementedError("Please implement the `attributes_to_check_for_spam` method. Should return the list of attributes to check.")

    def embeds_to_check_for_spam(self):
        return []

    def post_marked_as_no_spam(self):
        # Override to send delayed notification for exemple
        pass

def spam_protected(model=None):
    def decorator(f):
        def protected_function(*args, **kwargs):
            base_model = args[0]
            if model:
                model_to_check = model(*args, **kwargs)
            else:
                model_to_check = base_model

            if not isinstance(model_to_check, SpamMixin):
                raise ValueError("@spam_protected should be called within a SpamMixin. " + type(self).__name__ + " given.")

            if model_to_check.is_spam():
                model_to_check.spam.callbacks[f.__name__] = {
                    'args': args[1:],
                    'kwargs': kwargs
                }
                # At this point we recall `detect_spam`, I don't think it's a problem but to keep in mind there is kind of a loop here.
                # Here we call save() on the base model because we cannot save an embed document.
                base_model.save()
            else:
                f(*args, **kwargs)

        return protected_function
    return decorator

signals.pre_save.connect(SpamMixin.detect_spam_listener)
