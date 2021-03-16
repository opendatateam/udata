from flask import url_for

from udata_gouvfr.tests.frontend import GouvfrFrontTestCase
from udata_gouvfr.tests import GouvFrSettings

from udata.tests.frontend.test_csv import blueprint as testcsv


class CsvTest(GouvfrFrontTestCase):
    settings = GouvFrSettings
    modules = ['admin']

    def create_app(self):
        app = super().create_app()
        app.register_blueprint(testcsv)
        return app

    def test_empty_stream_from_list(self):
        self.assert400(self.get(url_for('testcsv.from_list')))
