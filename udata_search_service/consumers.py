import logging
import os

from udata_search_service.domain.entities import Dataset, Organization, Reuse, Dataservice, Topic, Discussion, Post
from udata_search_service.infrastructure.utils import get_concat_title_org, log2p, mdstrip


CONSUMER_LOGGING_LEVEL = int(os.environ.get("CONSUMER_LOGGING_LEVEL", logging.INFO))


class DatasetConsumer(Dataset):
    @classmethod
    def load_from_dict(cls, data):
        # Strip markdown
        data["description"] = mdstrip(data["description"])

        # Retrieve schema renamed as schema_
        data["schema"] = data.get("schema_") or data.get("schema")

        organization = data["organization"]
        data["organization"] = organization.get('id') if organization else None
        data["orga_followers"] = organization.get('followers') if organization else None
        data["orga_sp"] = organization.get('public_service') if organization else None
        data["organization_name"] = organization.get('name') if organization else None
        data["organization_badges"] = organization.get('badges') if organization else None

        resources = data["resources"]
        data["resources_ids"] = [res.get("id") for res in resources]
        data["resources_titles"] = [res.get("title") for res in resources]
        del data["resources"]

        data["concat_title_org"] = get_concat_title_org(data["title"], data['acronym'], data['organization_name'])
        data["geozones"] = [zone.get("id") for zone in data.get("geozones", [])]

        # Normalize values
        data["views"] = log2p(data.get("views", 0))
        data["followers"] = log2p(data.get("followers", 0))
        data["reuses"] = log2p(data.get("reuses", 0))
        data["orga_followers"] = log2p(data.get("orga_followers", 0))
        data["orga_sp"] = 4 if data.get("orga_sp", 0) else 1
        data["featured"] = 4 if data.get("featured", 0) else 1

        return super().load_from_dict(data)


class ReuseConsumer(Reuse):
    @classmethod
    def load_from_dict(cls, data):
        # Strip markdown
        data["description"] = mdstrip(data["description"])

        organization = data["organization"]
        data["organization"] = organization.get('id') if organization else None
        data["orga_followers"] = organization.get('followers') if organization else None
        data["organization_name"] = organization.get('name') if organization else None
        data["organization_badges"] = organization.get('badges') if organization else None

        # Normalize values
        data["views"] = log2p(data.get("views", 0))
        data["followers"] = log2p(data.get("followers", 0))
        data["orga_followers"] = log2p(data.get("orga_followers", 0))
        return super().load_from_dict(data)


class OrganizationConsumer(Organization):
    @classmethod
    def load_from_dict(cls, data):
        # Strip markdown
        data["description"] = mdstrip(data["description"])

        data["followers"] = log2p(data.get("followers", 0))
        data["views"] = log2p(data.get("views", 0))
        data["orga_sp"] = 4 if data.get("orga_sp", 0) else 1
        return super().load_from_dict(data)


class DataserviceConsumer(Dataservice):
    @classmethod
    def load_from_dict(cls, data):
        # Strip markdown
        data["description"] = mdstrip(data["description"])
        data["description_length"] = len(data["description"])

        organization = data["organization"]
        data["organization"] = organization.get('id') if organization else None
        data["orga_followers"] = organization.get('followers') if organization else None
        data["organization_name"] = organization.get('name') if organization else None

        # Normalize values
        data["views"] = log2p(data.get("views", 0))
        data["followers"] = log2p(data.get("followers", 0))
        data["orga_followers"] = log2p(data.get("orga_followers", 0))
        data["description_length"] = log2p(data["description_length"])

        return super().load_from_dict(data)


class TopicConsumer(Topic):
    @classmethod
    def load_from_dict(cls, data):
        # Strip markdown from description if any
        if data.get("description"):
            data["description"] = mdstrip(data["description"])
        return super().load_from_dict(data)


class DiscussionConsumer(Discussion):
    @classmethod
    def load_from_dict(cls, data):
        # No specific processing needed for discussions
        return super().load_from_dict(data)


class PostConsumer(Post):
    @classmethod
    def load_from_dict(cls, data):
        # Strip markdown from content if any
        if data.get("content"):
            data["content"] = mdstrip(data["content"])
        if data.get("headline"):
            data["headline"] = mdstrip(data["headline"])
        return super().load_from_dict(data)
