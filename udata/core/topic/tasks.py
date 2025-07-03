from udata.core.topic.models import Topic
from udata.tasks import job


@job("purge-topics-elements")
def purge_topics_elements(self):
    """
    Purge topic elements that have neither title nor element
    This should run *after* the purge-reuses and purge-datasets jobs
    """
    Topic.objects().update(pull__elements={"$and": [{"element": None}, {"title": None}]})
