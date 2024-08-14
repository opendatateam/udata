import json
import re

from udata.tests import DBTestMixin, TestCase, WebTestMixin


class FrontTestCase(WebTestMixin, DBTestMixin, TestCase):
    modules = []

    def get_json_ld(self, response):
        # In the pattern below, we extract the content of the JSON-LD script
        # The first ? is used to name the extracted string
        # The second ? is used to express the non-greediness of the extraction
        pattern = (
            r'<script id="json_ld" type="application/ld\+json">'
            r"(?P<json_ld>[\s\S]*?)"
            r"</script>"
        )
        data = response.data.decode("utf8")
        search = re.search(pattern, data)
        self.assertIsNotNone(search, (pattern, data))
        json_ld = search.group("json_ld")
        return json.loads(json_ld)
