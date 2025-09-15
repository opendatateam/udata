from udata.factories import ModelFactory

from .models import Page


class PageFactory(ModelFactory):
    class Meta:
        model = Page

    blocs = []
