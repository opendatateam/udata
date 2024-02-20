import logging
from datetime import datetime

from udata.models import db
from udata.core.spam.models import SpamMixin, spam_protected
from .signals import (on_new_discussion, on_discussion_closed, on_new_discussion_comment)


log = logging.getLogger(__name__)


COMMENT_SIZE_LIMIT = 50000


class Message(SpamMixin, db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.utcnow, required=True)
    posted_by = db.ReferenceField('User')

    def texts_to_check_for_spam(self):
        return [self.content]
    
    def spam_report_message(self, breadcrumb):
        message =  f"Spam potentiel dans le message"
        if self.posted_by:
            message += f" de [{self.posted_by.fullname}]({self.posted_by.external_url})"

        if len(breadcrumb) != 2:
            log.warning(f"`spam_report_message` called on message with a breadcrumb of {len(breadcrumb)} elements.", extra={ 'breadcrumb': breadcrumb})
            return message
        
        discussion = breadcrumb[0]
        if not isinstance(discussion, Discussion):
            log.warning(f"`spam_report_message` called on message with a breadcrumb not containing a Discussion at index 0.", extra={ 'breadcrumb': breadcrumb})
            return message

        message += f" sur la discussion « [{discussion.title}]({discussion.external_url}) »"
        return message


class Discussion(SpamMixin, db.Document):
    user = db.ReferenceField('User')
    subject = db.GenericReferenceField()
    title = db.StringField(required=True)
    discussion = db.ListField(db.EmbeddedDocumentField(Message))
    created = db.DateTimeField(default=datetime.utcnow, required=True)
    closed = db.DateTimeField()
    closed_by = db.ReferenceField('User')
    extras = db.ExtrasField()

    meta = {
        'indexes': [
            'user',
            'subject',
            '-created'
        ],
        'ordering': ['-created'],
    }

    def person_involved(self, person):
        """Return True if the given person has been involved in the

        discussion, False otherwise.
        """
        return any(message.posted_by == person for message in self.discussion)

    def texts_to_check_for_spam(self):
        # Discussion should always have a first message but it's not the case in some tests…
        return [self.title, self.discussion[0].content if len(self.discussion) else '']
    
    def embeds_to_check_for_spam(self):
        return self.discussion[1:]

    @property
    def external_url(self):
        return self.subject.url_for(
            _anchor='discussion-{id}'.format(id=self.id),
            _external=True)
    
    def spam_report_message(self, breadcrumb):
        message =  f"Spam potentiel sur la discussion « [{self.title}]({self.external_url}) »"
        if self.user:
            message += f" de [{self.user.fullname}]({self.user.external_url})"

        return message
    
    @spam_protected()
    def signal_new(self):
        on_new_discussion.send(self)

    @spam_protected(lambda discussion, message: discussion.discussion[message])
    def signal_close(self, message):
        on_discussion_closed.send(self, message=message)

    @spam_protected(lambda discussion, message: discussion.discussion[message])
    def signal_comment(self, message):
        on_new_discussion_comment.send(self, message=message)
