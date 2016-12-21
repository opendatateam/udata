# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import httpretty

from flask import url_for


from udata.tests.api import APITestCase
from udata.tests.factories import faker

from udata.settings import Testing

CROQUEMORT_URL = 'http://check.test'
CHECK_ONE_URL = CROQUEMORT_URL + '/check/one'
METADATA_URL = CROQUEMORT_URL + '/url'


def metadata_factory(url, status, content_type=None):
    return json.dumps({
      'etag': '',
      'url': url,
      'content-length': faker.pyint(),
      'content-disposition': '',
      'content-md5': faker.md5(),
      'content-location': '',
      'expires': faker.iso8601(),
      'status': str(status),
      'updated': faker.iso8601(),
      'last-modified': faker.iso8601(),
      'content-encoding': 'gzip',
      'content-type': content_type or faker.mime_type()
    })


class CheckUrlSettings(Testing):
    CROQUEMORT = {'url': CROQUEMORT_URL}


class CheckUrlAPITest(APITestCase):
    settings = CheckUrlSettings

    # def setUp(self):
    #     super(CheckUrlAPITest, self).setUp()
    #     self.config_backup = self.app.config.get('CROQUEMORT')
    #     self.croquemort_url = 'http://check.test'
    #     self.app.config['CROQUEMORT'] = {'url': self.croquemort_url}
    #
    # def tearDown(self):
    #     self.app.config['CROQUEMORT'] = self.config_backup

    @httpretty.activate
    def test_returned_metadata(self):
        url = faker.uri()
        url_hash = 'abcdef'
        content_type = 'text/html; charset=utf-8'
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body=json.dumps({'url-hash': url_hash}),
                               content_type='application/json')
        httpretty.register_uri(httpretty.GET, METADATA_URL + '/' + url_hash,
                               body=metadata_factory(url, 200,
                                                     content_type=content_type),
                               content_type='application/json')
        response = self.get(url_for('api.checkurl'), qs={'url': url})
        self.assert200(response)
        self.assertEqual(response.json['status'], '200')
        self.assertEqual(response.json['url'], url)
        self.assertEqual(response.json['content-type'], content_type)

    @httpretty.activate
    def test_invalid_url(self):
        url = faker.uri()
        url_hash = 'abcdef'
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body=json.dumps({'url-hash': url_hash}),
                               content_type='application/json')
        httpretty.register_uri(httpretty.GET, METADATA_URL + '/' + url_hash,
                               body=metadata_factory(url, 503),
                               content_type='application/json')
        response = self.get(url_for('api.checkurl'), qs={'url': url})
        self.assertStatus(response, 500)
        self.assertEqual(response.json['status'], '503')

    @httpretty.activate
    def test_delayed_url(self):
        url = faker.uri()
        url_hash = 'abcdef'
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body=json.dumps({'url-hash': url_hash}),
                               content_type='application/json')
        httpretty.register_uri(httpretty.GET, METADATA_URL + '/' + url_hash,
                               body=metadata_factory(url, 502),
                               content_type='application/json')
        response = self.get(url_for('api.checkurl'), qs={'url': url})
        self.assertStatus(response, 502)
        self.assertEqual(
            response.json['error'],
            'We were unable to retrieve the URL after 10 attempts.')
