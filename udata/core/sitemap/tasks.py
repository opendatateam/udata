from udata.tasks import job

from .generator import generate_sitemaps


@job("generate-sitemaps")
def generate_sitemaps_task(self):
    generate_sitemaps()
