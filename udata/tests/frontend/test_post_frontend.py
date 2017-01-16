# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.post.factories import PostFactory

from . import FrontTestCase


class OrganizationBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the post list page'''
        # with self.autoindex():
        posts = [PostFactory() for i in range(3)]

        response = self.get(url_for('posts.list'))

        self.assert200(response)
        rendered_posts = self.get_context_variable('posts')
        self.assertEqual(len(rendered_posts), len(posts))

    def test_render_list_empty(self):
        '''It should render the post list page event if empty'''
        response = self.get(url_for('posts.list'))
        self.assert200(response)

    def test_render_display(self):
        '''It should render the post page'''
        post = PostFactory()
        response = self.get(url_for('posts.show', post=post))
        self.assert200(response)
