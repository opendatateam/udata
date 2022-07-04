from typing import Optional
from flask import request, redirect, abort, g
from flask.views import MethodView

from udata import search, auth
from udata.utils import not_none_dict
from udata_front import theme


class Templated(object):
    template_name: Optional[str] = None

    def get_context(self):
        return {}

    def get_template_name(self):
        return self.template_name

    def render(self, context=None, **kwargs):
        context = context or self.get_context()
        context.update(kwargs)
        return theme.render(self.get_template_name(), **context)


class BaseView(MethodView):
    require = None

    def dispatch_request(self, *args, **kwargs):
        self.kwargs = kwargs
        self.set_identity(g.identity)
        if not self.can(*args, **kwargs):
            return abort(403)
        return super(BaseView, self).dispatch_request(*args, **kwargs)

    def can(self, *args, **kwargs):
        '''Overwrite this method to implement custom contextual permissions'''
        if isinstance(self.require, auth.Permission):
            return self.require.can()
        elif callable(self.require):
            return self.require()
        elif isinstance(self.require, bool):
            return self.require
        else:
            return True

    def set_identity(self, *args, **kwargs):
        pass


class ListView(Templated, BaseView):
    '''
    Render a Queryset as a list.
    '''
    model = None
    context_name = 'objects'
    default_page_size = 20

    def get_queryset(self):
        return self.model.objects

    def get_context(self):
        context = super(ListView, self).get_context()
        context[self.context_name] = self.get_queryset()
        return context

    @property
    def page(self):
        try:
            params_page = int(request.args.get('page', 1) or 1)
            return max(params_page, 1)
        except ValueError:  # Cast exception
            # Failsafe, if page cannot be parsed, we falback on first page
            return 1

    @property
    def page_size(self):
        try:
            params_page_size = request.args.get('page_size',
                                                self.default_page_size)
            return int(params_page_size or self.default_page_size)
        except ValueError:  # Cast exception
            # Failsafe, if page_size cannot be parsed, we falback on default
            return self.default_page_size

    def get(self, **kwargs):
        return self.render()


class SearchView(Templated, BaseView):
    '''
    Render a Queryset as a list.
    '''
    model = None
    context_name = 'objects'
    search_adapter = None
    page_size: Optional[int] = None

    def get_queryset(self):
        parser = self.search_adapter.as_request_parser()
        if self.page_size:
            parser.replace_argument('page_size', type=int, location='args', default=self.page_size)
        return search.query(self.search_adapter, **not_none_dict(parser.parse_args()))

    def get_context(self):
        context = super(SearchView, self).get_context()
        context[self.context_name] = self.get_queryset()
        return context

    def get(self, **kwargs):
        return self.render()


class SingleObject(object):
    model = None
    object_name = 'object'
    object = None

    def get_object(self):
        if not self.object:
            if self.object_name in self.kwargs:
                self.object = self.kwargs[self.object_name]
            if 'slug' in self.kwargs:
                self.object = self.model.objects.get_or_404(
                    slug=self.kwargs.get('slug'))
            elif 'id' in self.kwargs:
                self.object = self.model.objects.get_or_404(
                    self.kwargs.get('id'))
        return self.object

    def get_context(self):
        context = super(SingleObject, self).get_context()
        context[self.object_name] = self.get_object()
        return context


class NestedObject(SingleObject):
    nested_model = None
    nested_object_name = 'nested'
    _nested_object = None
    nested_attribute = None
    nested_id = None

    @property
    def nested_object(self):
        if not self._nested_object:
            obj = self.get_object()
            if not self.nested_attribute:
                raise ValueError('nested_attribute should be set')
            if self.nested_object_name in self.kwargs:
                self.nested_id = self.kwargs[self.nested_object_name]
            nested = getattr(obj, self.nested_attribute)
            if isinstance(nested, (list, tuple)):
                for item in nested:
                    if self.is_nested(item):
                        self._nested_object = item
                        break
            else:
                self.nested_object = nested
        return self._nested_object

    def is_nested(self, obj):
        return str(obj.id) == self.nested_id

    def get_context(self):
        context = super(NestedObject, self).get_context()
        context[self.nested_object_name] = self.nested_object
        return context


class DetailView(SingleObject, Templated, BaseView):
    '''
    Render a single object.
    '''

    def get(self, **kwargs):
        return self.render()

    def get_context(self):
        context = super(DetailView, self).get_context()

        if hasattr(self.object, 'json_ld'):
            context['json_ld'] = self.object.json_ld
        return context


class FormView(Templated, BaseView):
    form = None

    def get_context(self):
        context = super(FormView, self).get_context()
        form = self.get_form(request.form)
        context['form'] = self.initialize_form(form)
        return context

    def get_form(self, data, obj=None):
        return self.form(data, obj=obj)

    def initialize_form(self, form):
        return form

    def get(self, **kwargs):
        return self.render()

    def on_form_valid(self, form):
        return redirect(self.get_success_url())

    def on_form_error(self, form):
        return self.render(form=form)

    def get_success_url(self, obj):
        return obj.display_url

    def post(self, **kwargs):
        context = self.get_context()
        form = context['form']

        if form.validate():
            return self.on_form_valid(form)

        return self.on_form_error(form)
