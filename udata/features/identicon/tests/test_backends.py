# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.features.identicon.backends import internal

from udata.tests import TestCase, WebTestMixin
from udata.utils import faker


class InternalBackendTests(WebTestMixin, TestCase):
    def assert_stream_equal(self, response1, response2):
        self.assertEqual(list(response1.iter_encoded()),
                         list(response2.iter_encoded()))

    def test_base_rendering(self):
        response = internal(faker.word(), 32)
        self.assert200(response)
        self.assertEqual(response.mimetype, 'image/png')
        self.assertTrue(response.is_streamed)

    def test_render_twice_the_same(self):
        identifier = faker.word()
        self.assert_stream_equal(internal(identifier, 32),
                                 internal(identifier, 32))
