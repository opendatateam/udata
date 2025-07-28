class Linkable:
    def _link_id(self, **kwargs):
        if kwargs.get("_useId", False):
            return self.id

        # Some old/special datasets don't have slug?
        return self.slug or self.id

    def _self_api_url_kwargs(self, **kwargs):
        # Default to external
        kwargs["_external"] = kwargs.pop("_external", True)

        # Remove own private data
        kwargs.pop("_useId", None)
        kwargs.pop("_mailCampaign", None)

        return kwargs

    def url_for(self, **kwargs):
        return self.self_web_url(**kwargs) or self.self_api_url(**kwargs)
