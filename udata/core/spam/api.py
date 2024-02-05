from udata.api import api, API
from udata.utils import id_or_404
from udata.auth import admin_permission

class SpamAPI(API):
    '''
    Base Spam Model API.
    '''
    model = None

    def get_model(self, id):
        '''This function returns the base model and the spamable model which can be different. The base model is the model stored inside Mongo and the spamable model is the embed document (for exemple a comment inside a discussion)'''
        model = self.model.objects.get_or_404(id=id_or_404(id))
        return model, model

    @api.secure(admin_permission)
    def delete(self, **kwargs):
        '''Mark a potentiel spam as no spam'''
        base_model, model = self.get_model(**kwargs)

        if not model.is_spam():
            return {}, 200
        
        model.mark_as_no_spam(base_model)
        return {}, 200
