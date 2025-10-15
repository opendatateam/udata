from udata.tests import DBTestMixin, TestCase, WebTestMixin


class FrontTestCase(WebTestMixin, DBTestMixin, TestCase):
    pass
