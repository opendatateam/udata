# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.user.factories import AdminFactory
from udata.tests.api import APITestCase


class PostsAPITest(APITestCase):
    modules = ['core.dataset', 'core.reuse', 'core.user', 'core.post']

    def test_post_api_list(self):
        '''It should fetch a post list from the API'''
        posts = PostFactory.create_batch(3)

        response = self.get(url_for('api.posts'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(posts))

    def test_post_api_get(self):
        '''It should fetch a post from the API'''
        post = PostFactory()
        response = self.get(url_for('api.post', post=post))
        self.assert200(response)

    def test_post_api_create(self):
        '''It should create a post from the API'''
        data = PostFactory.as_dict()
        data['datasets'] = [str(d.id) for d in data['datasets']]
        data['reuses'] = [str(r.id) for r in data['reuses']]
        self.login(AdminFactory())
        response = self.post(url_for('api.posts'), data)
        self.assert201(response)
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        for dataset, expected in zip(post.datasets, data['datasets']):
            self.assertEqual(str(dataset.id), expected)
        for reuse, expected in zip(post.reuses, data['reuses']):
            self.assertEqual(str(reuse.id), expected)

    def test_post_api_update(self):
        '''It should update a post from the API'''
        post = PostFactory()
        data = post.to_dict()
        data['content'] = 'new content'
        self.login(AdminFactory())
        response = self.put(url_for('api.post', post=post), data)
        self.assert200(response)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().content, 'new content')

    def test_post_api_delete(self):
        '''It should delete a post from the API'''
        post = PostFactory()
        with self.api_user(AdminFactory()):
            response = self.delete(url_for('api.post', post=post))
        self.assertStatus(response, 204)
        self.assertEqual(Post.objects.count(), 0)
