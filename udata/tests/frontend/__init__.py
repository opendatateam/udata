import json
import re
import pytest

from udata.tests import TestCase, WebTestMixin, SearchTestMixin


class FrontTestCase(WebTestMixin, SearchTestMixin, TestCase):
    modules = []

    @pytest.fixture(autouse=True)
    def inject_templates(self, templates):
        self.templates = templates

    def get_json_ld(self, response):
        # In the pattern below, we extract the content of the JSON-LD script
        # The first ? is used to name the extracted string
        # The second ? is used to express the non-greediness of the extraction
        pattern = (r'<script id="json_ld" type="application/ld\+json">'
                   r'(?P<json_ld>[\s\S]*?)'
                   r'</script>')
        data = response.data.decode('utf8')
        search = re.search(pattern, data)
        self.assertIsNotNone(search, (pattern, data))
        json_ld = search.group('json_ld')
        return json.loads(json_ld)

    def assertTemplateUsed(self, name):
        """
        Checks if a given template is used in the request.

        :param name: template name
        """
        __tracebackhide__ = True
        self.templates.assert_used(name)

    def get_context_variable(self, name):
        """
        Returns a variable from the context passed to the template.

        :param name: name of variable
        :raises ContextVariableDoesNotExist: if does not exist.
        """
        return self.templates.get_context_variable(name)
