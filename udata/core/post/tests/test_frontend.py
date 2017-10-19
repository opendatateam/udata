# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.post.factories import PostFactory
from udata.tests.frontend import FrontTestCase
from udata.utils import faker


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

    def test_render_display_without_navigation(self):
        '''It should not render post navigation if not necessary'''
        post = PostFactory()
        response = self.get(url_for('posts.show', post=post))
        self.assert200(response)
        self.assertNotIn('nav-section', response.data.decode('utf-8'))

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

    def test_render_display_with_siblings(self):
        '''It should render the post page with sibling links'''
        previous_date = faker.date_time_between(start_date='-3d',
                                                end_date='-2d')
        date = faker.date_time_between(start_date='-2d', end_date='-1d')
        next_date = faker.date_time_between(start_date='-1d', end_date='now')
        other_date = faker.date_time_between(start_date='-1y', end_date='-3d')

        previous_post = PostFactory(created_at=previous_date)
        post = PostFactory(created_at=date)
        next_post = PostFactory(created_at=next_date)
        PostFactory.create_batch(3, created_at=other_date)

        response = self.get(url_for('posts.show', post=post))

        self.assert200(response)
        self.assertEqual(self.get_context_variable('previous_post'),
                         previous_post)
        self.assertEqual(self.get_context_variable('next_post'), next_post)
