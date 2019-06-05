# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from flask import url_for

from udata.models import Discussion, Message
from udata.core.dataset.factories import DatasetFactory
from udata.settings import Testing


class LimiterSettings(Testing):
    RATELIMIT_ENABLED = True
    RATELIMIT_DISCUSSIONS = '0/minute'


@pytest.mark.usefixtures('clean_db')
class APILimiterTest:
    modules = []
    settings = LimiterSettings

    def test_limit_dicussions(self, api):
        '''Test rate limiting on discussions'''
        api.login()
        dataset = DatasetFactory()
        response = api.post(url_for('api.discussions'), {
            'title': 'test title',
            'comment': 'bla bla',
            'subject': {
                'class': 'Dataset',
                'id': dataset.id,
            }
        })
        assert response.status_code == 429

    def test_limit_comments(self, api):
        user = api.login()
        dataset = DatasetFactory()
        message = Message(content='bla bla', posted_by=user)
        discussion = Discussion.objects.create(
            subject=dataset,
            user=user,
            title='test discussion',
            discussion=[message]
        )
        response = api.post(url_for('api.discussion', **{'id': discussion.id}), {
            'comment': 'new bla bla'
        })
        assert response.status_code == 429
