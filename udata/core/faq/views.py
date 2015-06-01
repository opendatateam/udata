# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.frontend.views import BaseView, Templated
from udata.app import Blueprint

bp = Blueprint('faq', __name__, url_prefix='/faq')


class FAQBaseView(Templated, BaseView):

    def get(self, **kwargs):
        return self.render()


@bp.route('/', endpoint='home')
class HomeView(FAQBaseView):
    template_name = 'faq/home.html'


@bp.route('/citizen/', endpoint='citizen')
class CitizenView(FAQBaseView):
    template_name = 'faq/citizen.html'


@bp.route('/producer/', endpoint='producer')
class ProducerView(FAQBaseView):
    template_name = 'faq/producer.html'


@bp.route('/developer/', endpoint='developer')
class DeveloperView(FAQBaseView):
    template_name = 'faq/developer.html'


@bp.route('/jurist/', endpoint='jurist')
class JuristView(FAQBaseView):
    template_name = 'faq/jurist.html'
