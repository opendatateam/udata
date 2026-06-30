from dataclasses import dataclass
from xml.etree import ElementTree

from flask import current_app

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.core.topic.models import Topic
from udata.storage.s3 import store_bytes

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

BATCH_SIZE = 1000

S3_PUBLIC_ACL = "public-read"


@dataclass
class SitemapConfig:
    name: str
    model: type
    queryset_filter: str
    only_fields: list[str]
    lastmod_attr: str


_SITEMAP_CONFIGS = [
    SitemapConfig(
        "datasets", Dataset, "visible", ["slug", "last_modified_internal"], "last_modified_internal"
    ),
    SitemapConfig(
        "organizations", Organization, "visible", ["slug", "last_modified"], "last_modified"
    ),
    SitemapConfig("reuses", Reuse, "visible", ["slug", "last_modified"], "last_modified"),
    SitemapConfig("posts", Post, "published", ["slug", "last_modified"], "last_modified"),
    SitemapConfig(
        "dataservices",
        Dataservice,
        "visible",
        ["slug", "metadata_modified_at"],
        "metadata_modified_at",
    ),
    SitemapConfig("topics", Topic, "visible", ["slug", "last_modified"], "last_modified"),
]


def render_xml(root_tag, items, child_tag):
    root = ElementTree.Element(root_tag, xmlns=SITEMAP_NS)
    for item in items:
        child = ElementTree.SubElement(root, child_tag)
        ElementTree.SubElement(child, "loc").text = item["loc"]
        if item.get("lastmod"):
            ElementTree.SubElement(child, "lastmod").text = item["lastmod"]
    ElementTree.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>' + ElementTree.tostring(root, encoding="unicode")


def _iter_urls(qs, only_fields, lastmod_attr):
    for obj in qs.only(*only_fields).batch_size(BATCH_SIZE).no_cache().timeout(False):
        lastmod = getattr(obj, lastmod_attr)
        yield {"loc": obj.self_web_url(), "lastmod": lastmod.isoformat() if lastmod else None}


def _iter_chunks(urls, size):
    chunk = []
    for url in urls:
        chunk.append(url)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def generate_sitemaps():
    bucket = current_app.config["SITEMAP_S3_BUCKET"]
    if not bucket:
        current_app.logger.warning("SITEMAP_S3_BUCKET not configured, skipping sitemap generation")
        return False

    if not current_app.config.get("CDATA_BASE_URL"):
        current_app.logger.warning("CDATA_BASE_URL not configured, skipping sitemap generation")
        return False

    base_url = current_app.config.get("SITEMAP_BASE_URL")
    if not base_url:
        current_app.logger.warning("SITEMAP_BASE_URL not configured, skipping sitemap generation")
        return False

    prefix = current_app.config["SITEMAP_S3_FILENAME_PREFIX"].strip("/")
    max_per_file = current_app.config["SITEMAP_URLS_PER_FILE"]

    index_files = []
    total_urls = 0

    for config in _SITEMAP_CONFIGS:
        qs = config.model.objects
        if config.queryset_filter:
            qs = getattr(qs, config.queryset_filter)()
        for index, chunk in enumerate(
            _iter_chunks(_iter_urls(qs, config.only_fields, config.lastmod_attr), max_per_file), 1
        ):
            filename = f"{config.name}_{index}.xml"
            store_bytes(
                bucket,
                f"{prefix}/{filename}",
                render_xml("urlset", chunk, "url").encode("utf-8"),
                ACL=S3_PUBLIC_ACL,
                ContentType="application/xml",
            )
            index_files.append({"loc": f"{base_url}/{prefix}/{filename}"})
            total_urls += len(chunk)

    store_bytes(
        bucket,
        f"{prefix}/sitemap.xml",
        render_xml("sitemapindex", index_files, "sitemap").encode("utf-8"),
        ACL=S3_PUBLIC_ACL,
        ContentType="application/xml",
    )

    current_app.logger.info(f"Uploaded {len(index_files)} sitemap files ({total_urls} total URLs)")
    return True
