from datetime import datetime

from flask import current_app, request
from flask_security import current_user

from udata.api import api, API, fields
from udata.core.user.api_fields import user_ref_fields
from udata.utils import id_or_404

class SpamAPI(API):
    '''
    Base Spam Model API.
    '''
    model = None

    def get_model(self, id):
        model = self.model.objects.get_or_404(id=id_or_404(id))
        return model, model

    @api.secure
    def delete(self, **kwargs):
        '''Mark a potentiel spam as no spam'''
        base_model, model = self.get_model(**kwargs)

        if not model.is_spam():
            return {}, 200
        
        model.mark_as_no_spam(base_model)
        return {}, 200
