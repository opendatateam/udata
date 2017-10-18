# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.post.factories import PostFactory
from udata.tests.frontend import FrontTestCase


class PostBlueprintTest(FrontTestCase):
    modules = ['core.post', 'admin', 'core.dataset', 'core.reuse',
               'core.site', 'core.organization', 'search']

    def test_render_list(self):
        '''It should render the post list page'''
        posts = PostFactory.create_batch(3)

        response = self.get(url_for('posts.list'))

        self.assert200(response)
        rendered_posts = self.get_context_variable('posts')
        self.assertEqual(len(rendered_posts), len(posts))

    def test_render_list_empty(self):
        '''It should render the post list page event if empty'''
        response = self.get(url_for('posts.list'))
        self.assert200(response)

    def test_render_display_without_discussions(self):
        '''It should render the post page without discussions'''
        self.app.config['POST_DISCUSSIONS_ENABLED'] = False
        post = PostFactory()
        response = self.get(url_for('posts.show', post=post))
        self.assert200(response)
        self.assertNotIn('discussions-section', response.data.decode('utf-8'))

    def test_render_display_with_discussions(self):
        '''It should render the post page with discussions'''
        self.app.config['POST_DISCUSSIONS_ENABLED'] = True
        post = PostFactory()
        response = self.get(url_for('posts.show', post=post))
        self.assert200(response)
        self.assertIn('discussions-section', response.data.decode('utf-8'))
