from udata.commands.db import check_references
from udata.tasks import job


@job("check-integrity")
def check_integrity(self):
    check_references()
