import pytest

from flask import url_for

from udata.core.post.factories import PostFactory
from udata.tests.helpers import assert200
from udata.utils import faker

from udata_front.tests import GouvFrSettings


@pytest.mark.usefixtures('clean_db')
class PostBlueprintTest:
    settings = GouvFrSettings
    modules = ['admin']

    def test_render_list(self, client, templates):
        '''It should render the post list page'''
        posts = PostFactory.create_batch(3)

        response = client.get(url_for('posts.list'))

        assert200(response)
        rendered_posts = templates.get_context_variable('posts')
        assert len(rendered_posts) == len(posts)

    def test_render_list_empty(self, client):
        '''It should render the post list page event if empty'''
        response = client.get(url_for('posts.list'))
        assert200(response)

    def test_render_display_without_navigation(self, client):
        '''It should not render post navigation if not necessary'''
        post = PostFactory()
        response = client.get(url_for('posts.show', post=post))
        assert200(response)
        assert 'nav-section' not in response.data.decode('utf-8')

    @pytest.mark.options(POST_DISCUSSIONS_ENABLED=False)
    def test_render_display_without_discussions(self, client):
        '''It should render the post page without discussions'''
        post = PostFactory()
        response = client.get(url_for('posts.show', post=post))
        assert200(response)
        assert 'discussions-section' not in response.data.decode('utf-8')

    @pytest.mark.options(POST_DISCUSSIONS_ENABLED=True)
    def test_render_display_with_discussions(self, client):
        '''It should render the post page with discussions'''
        post = PostFactory()
        response = client.get(url_for('posts.show', post=post))
        assert200(response)
        assert 'discussions-section' in response.data.decode('utf-8')

    def test_render_display_with_siblings(self, client, templates):
        '''It should render the post page with sibling links'''
        previous_date = faker.date_time_between(start_date='-3d',
                                                end_date='-2d')
        date = faker.date_time_between(start_date='-2d', end_date='-1d')
        next_date = faker.date_time_between(start_date='-1d', end_date='now')
        other_date = faker.date_time_between(start_date='-1y', end_date='-3d')

        previous_post = PostFactory(published=previous_date)
        post = PostFactory(published=date)
        next_post = PostFactory(published=next_date)
        PostFactory.create_batch(3, published=other_date)

        response = client.get(url_for('posts.show', post=post))

        assert200(response)
        assert templates.get_context_variable('previous_post') == previous_post
        assert templates.get_context_variable('next_post') == next_post
