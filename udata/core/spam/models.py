import logging
from flask import current_app
from mongoengine import signals

from udata.models import db

NOT_CHECKED = 'not_checked'
POTENTIEL_SPAM = 'potentiel_spam'
NO_SPAM = 'no_spam'

class SpamInfo(db.EmbeddedDocument):
    status = db.StringField(choices=[NOT_CHECKED, POTENTIEL_SPAM, NO_SPAM], default=NOT_CHECKED)
    callbacks = db.DictField(default={})

class SpamMixin(object):
    spam = db.EmbeddedDocumentField(SpamInfo)

    @staticmethod
    def spam_words():
        return current_app.config.get('SPAM_WORDS', [])

    def detect_spam_listener(sender, document):
        '''This is the callback called on MongoEngine pre_save() for all models of the application'''
        if not isinstance(document, SpamMixin):
            return

        document.detect_spam()

    def detect_spam(self):
        """
        This is the main function doing the spam detection.
        This function set a flag POTENTIEL_SPAM if a model is suspicious.
        """

        # During initialisation some models can have no spam associated
        if not self.spam:
            self.spam = SpamInfo(status=NOT_CHECKED, callbacks={})

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
        if not self._get_changed_fields() or not all(field.startswith('spam.') for field in self._get_changed_fields()):
            for text in self.attributes_to_check_for_spam():
                for word in SpamMixin.spam_words():
                    if word in text:
                        self.spam.status = POTENTIEL_SPAM
                        return

        for embed in self.embeds_to_check_for_spam():
            embed.detect_spam()

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
        return self.spam and self.spam.status == POTENTIEL_SPAM
    
    def attributes_to_check_for_spam(self):
        raise NotImplementedError("Please implement the `attributes_to_check_for_spam` method. Should return the list of attributes to check.")

    def embeds_to_check_for_spam(self):
        return []

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

# Register a signal for all app models. This may be ineficient (we do a custom check at the beginning of the listener
# to early return of non `SpamMixin`), but I didn't find a way to only register this signal for `SpamMixin` (problems with 
# Python circular dependencies or force the user to connect manualy to the signal for each implementation of SpamMixin).
signals.pre_save.connect(SpamMixin.detect_spam_listener)
