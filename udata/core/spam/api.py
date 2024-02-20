from mongoengine import Q

from udata.api import api, API
from udata.auth import admin_permission
from udata.core.discussions.models import Discussion
from udata.core.spam.fields import potential_spam_fields
from udata.core.spam.models import POTENTIAL_SPAM
from udata.utils import id_or_404


class SpamAPIMixin(API):
    """
    Base Spam Model API.
    """
    model = None

    def get_model(self, id):
        """
        This function returns the base model and the spamable model which can be different. The base model is the
        model stored inside Mongo and the spamable model is the embed document (for example a comment inside a
        discussion)
        """
        model = self.model.objects.get_or_404(id=id_or_404(id))
        return model, model

    @api.secure(admin_permission)
    def delete(self, **kwargs):
        """
        Mark a potential spam as no spam
        """
        base_model, model = self.get_model(**kwargs)

        if not model.is_spam():
            return {}, 200

        model.mark_as_no_spam(base_model)
        return {}, 200


ns = api.namespace('spam', 'Spam related operations')


@ns.route('/', endpoint='spam')
class SpamAPI(API):
    """
    Base class for a discussion thread.
    """
    @api.doc('get_potential_spams')
    @api.secure(admin_permission)
    @api.marshal_with(potential_spam_fields)
    def get(self):
        """Get all potential spam objects"""
        discussions = Discussion.objects(Q(spam__status=POTENTIAL_SPAM) | Q(discussion__spam__status=POTENTIAL_SPAM))

        return [{
            'message': discussion.spam_report_message([discussion]),
        } for discussion in discussions]
