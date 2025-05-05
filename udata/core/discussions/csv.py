from udata.core import csv

from .models import Discussion


@csv.adapter(Discussion)
class DiscussionCsvAdapter(csv.Adapter):
    fields = (
        "id",
        "user",
        "subject",
        ("subject_class", "subject._class_name"),
        ("subject_id", "subject.id"),
        "title",
        ("size", lambda o: len(o.discussion)),
        ("participants", lambda o: ",".join(set(str(msg.posted_by.id) for msg in o.discussion))),
        ("messages", lambda o: "\n".join(msg.content.replace("\n", " ") for msg in o.discussion)),
        "created",
        "closed",
        "closed_by",
        ("closed_by_id", "closed_by.id"),
        "closed_by_organization",
        ("closed_by_organization_id", "closed_by_organization.id"),
    )
