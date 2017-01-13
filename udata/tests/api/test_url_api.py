# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import httpretty
import requests

from flask import url_for


from udata.tests.api import APITestCase
from udata.utils import faker

from udata.settings import Testing

CROQUEMORT_URL = 'http://check.test'
CHECK_ONE_URL = '{0}/check/one'.format(CROQUEMORT_URL)
METADATA_URL = '{0}/url'.format(CROQUEMORT_URL)


def metadata_factory(url, data=None):
    response = {
      'etag': '',
      'url': url,
      'content-length': faker.pyint(),
      'content-disposition': '',
      'content-md5': faker.md5(),
      'content-location': '',
      'expires': faker.iso8601(),
      'status': 200,
      'updated': faker.iso8601(),
      'last-modified': faker.iso8601(),
      'content-encoding': 'gzip',
      'content-type': faker.mime_type()
    }
    if data:
        response.update(data)
    return json.dumps(response)


def mock_url_check(url, data=None, status=200):
    url_hash = faker.md5()
    httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                           body=json.dumps({'url-hash': url_hash}),
                           content_type='application/json')
    check_url = '/'.join((METADATA_URL, url_hash))
    httpretty.register_uri(httpretty.GET, check_url,
                           body=metadata_factory(url, data),
                           content_type='application/json',
                           status=status)


def exception_factory(exception):
    def callback(request, uri, headers):
        raise exception
    return callback


class CheckUrlSettings(Testing):
    CROQUEMORT = {
        'url': CROQUEMORT_URL,
        'retry': 2,
        'delay': 1,
    }


class CheckUrlAPITest(APITestCase):
    settings = CheckUrlSettings

    @httpretty.activate
    def test_returned_metadata(self):
        url = faker.uri()
        metadata = {
            'content-type': 'text/html; charset=utf-8',
            'status': 200,
        }
        mock_url_check(url, metadata)
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assert200(response)
        self.assertEqual(response.json['status'], 200)
        self.assertEqual(response.json['url'], url)
        self.assertEqual(response.json['content-type'],
                         'text/html; charset=utf-8')

    @httpretty.activate
    def test_invalid_url(self):
        url = faker.uri()
        mock_url_check(url, {'status': 503})
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assertStatus(response, 503)

    @httpretty.activate
    def test_delayed_url(self):
        url = faker.uri()
        mock_url_check(url, status=404)
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assertStatus(response, 500)
        self.assertEqual(
            response.json['error'],
            'We were unable to retrieve the URL after 2 attempts.')

    @httpretty.activate
    def test_timeout(self):
        url = faker.uri()
        exception = requests.Timeout('Request timed out')
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body=exception_factory(exception))
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assertStatus(response, 503)

    @httpretty.activate
    def test_connection_error(self):
        url = faker.uri()
        exception = requests.ConnectionError('Unable to connect')
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body=exception_factory(exception))
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assertStatus(response, 503)

    @httpretty.activate
    def test_json_error_check_one(self):
        url = faker.uri()
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body='<strong>not json</strong>',
                               content_type='test/html')
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assertStatus(response, 503)

    @httpretty.activate
    def test_json_error_check_url(self):
        url = faker.uri()
        url_hash = faker.md5()
        httpretty.register_uri(httpretty.POST, CHECK_ONE_URL,
                               body=json.dumps({'url-hash': url_hash}),
                               content_type='application/json')
        check_url = '/'.join((METADATA_URL, url_hash))
        httpretty.register_uri(httpretty.GET, check_url,
                               body='<strong>not json</strong>',
                               content_type='test/html')
        response = self.get(url_for('api.checkurl'),
                            qs={'url': url, 'group': ''})
        self.assertStatus(response, 500)
        self.assertIn('error', response.json)
