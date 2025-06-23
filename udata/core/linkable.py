class Linkable:
    def _link_id(self, **kwargs):
        return self.id if kwargs.get("_useId", False) else self.slug

    def url_for(self, **kwargs):
        return self.self_web_url(**kwargs) or self.self_api_url(**kwargs)
