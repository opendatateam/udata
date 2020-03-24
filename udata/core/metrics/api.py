from flask import abort

from udata.api import api, API


@api.route('/metrics/<id>', endpoint='metrics')
class MetricsAPI(API):

    def get(self, id):
        abort(501, 'This endpoint was deprecated because of metrics refactoring')
