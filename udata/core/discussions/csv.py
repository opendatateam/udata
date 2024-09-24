from udata.frontend import csv

from .models import Discussion


@csv.adapter(Discussion)
class DiscussionCsvAdapter(csv.Adapter):
    fields = (
        "id",
        "user",
        "subject",
        ("subject_class", "subject.class"),
        ("subject_id", "subject.id"),
        "title",
        ("size", lambda o: len(o.discussion)),
        (
            "participants",
            lambda o: ",".join(
                getattr(msg.posted_by, "class") + "_" + msg.posted_by.id for msg in o.discussion
            ),
        ),
        ("messages", lambda o: "\n".join(msg.content.replace("\n", " ") for msg in o.discussion)),
        "created",
        "closed",
        "closed_by",
    )
