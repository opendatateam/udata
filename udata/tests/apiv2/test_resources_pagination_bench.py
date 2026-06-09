"""
Micro-benchmark for the `/api/2/datasets/<id>/resources/` endpoint.

Goal: quantify whether the cost of the endpoint scales with the *total* number
of resources of the dataset (rather than with `page_size`), and locate where the
time is spent. This is a benchmark, not a regression test: run it explicitly with

    uv run pytest udata/tests/apiv2/test_resources_pagination_bench.py -s

The decomposition we measure, per resource count N:

  * fetch_only      : Dataset.objects.get_or_404(id)  -- what the URL converter
                      actually does. Transfers the whole BSON document (resources
                      included) and builds the top-level document, but does NOT
                      deserialize the embedded resources (MongoEngine is lazy).
  * fetch_deser     : same + iterate over `dataset.resources` to force the lazy
                      deserialization of every embedded Resource. This is what the
                      endpoint triggers when it reads `dataset.resources`.
  * fetch_excluded  : Dataset.objects.exclude("resources").get_or_404(id) -- the
                      cost if we never loaded the resources at all.
  * endpoint        : the full HTTP call with page_size=10 (converter + filter +
                      slice + marshalling of 10 + JSON + HTTP overhead).
  * aggregate       : the *proposed fix* -- a Mongo aggregation pipeline that
                      $matches the document, $filters resources by type server-side,
                      then $slices the page and $sizes the total. Only the 10 paged
                      resources cross the wire; they are re-wrapped as Resource
                      objects (needed for marshalling). $filter still walks the array
                      server-side (O(N) on the Mongo server), but the wire transfer
                      and the Python deserialization become O(page_size).

Derived:
  deser   = fetch_deser - fetch_only      (Python deserialization of embedded docs)
  bson    = fetch_only - fetch_excluded   (BSON transfer/build of the resources)
  rest    = endpoint - fetch_deser        (filter + slice + marshal 10 + JSON + HTTP)
"""

import statistics
import time
from datetime import datetime

from flask import url_for

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.models import Dataset, Resource
from udata.tests.api import APITestCase

REPEATS = 25
WARMUP = 3
RESOURCE_COUNTS = [0, 10, 50, 150, 300]


def _realistic_extras():
    """~16 extras keys, mirroring a real data.gouv.fr resource."""
    extras = {f"analysis:metric-{i}": i for i in range(10)}
    extras.update(
        {
            "check:available": True,
            "check:status": 200,
            "check:date": datetime(2024, 1, 1),
            "analysis:content-length": 53441749,
            "analysis:content-type": "application/zip",
            "analysis:last-modified-at": datetime(2024, 1, 1),
        }
    )
    return extras


def _timeit(fn):
    for _ in range(WARMUP):
        fn()
    samples = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)  # ms
    return statistics.median(samples)


class ResourcesPaginationBench(APITestCase):
    def test_bench(self):
        print("\n")
        header = (
            f"{'N res':>6} | {'fetch_only':>11} | {'fetch_deser':>11} | "
            f"{'excluded':>9} | {'endpoint':>9} | {'aggregate':>10} || "
            f"{'deser':>8} | {'bson':>7} | {'rest':>7}"
        )
        print(header)
        print("-" * len(header))

        for n in RESOURCE_COUNTS:
            resources = [ResourceFactory.build(extras=dict(_realistic_extras())) for _ in range(n)]
            dataset = DatasetFactory(resources=resources)
            did = str(dataset.id)
            oid = dataset.id

            def fetch_only():
                return Dataset.objects.get_or_404(id=did)

            def fetch_deser():
                d = Dataset.objects.get_or_404(id=did)
                for r in d.resources:
                    r.type  # force lazy deserialization of the embedded doc
                return d

            def fetch_excluded():
                return Dataset.objects.exclude("resources").get_or_404(id=did)

            def endpoint():
                response = self.get(
                    url_for(
                        "apiv2.resources",
                        dataset=did,
                        type="documentation",
                        page_size=10,
                    )
                )
                assert response.status_code == 200, response.status_code
                return response

            def aggregate():
                pipeline = [
                    {"$match": {"_id": oid}},
                    {
                        "$project": {
                            "filtered": {
                                "$filter": {
                                    "input": "$resources",
                                    "as": "r",
                                    "cond": {"$eq": ["$$r.type", "documentation"]},
                                }
                            }
                        }
                    },
                    {
                        "$project": {
                            "total": {"$size": "$filtered"},
                            "data": {"$slice": ["$filtered", 0, 10]},
                        }
                    },
                ]
                result = next(Dataset.objects.aggregate(*pipeline))
                # re-wrap the paged dicts as Resource objects, as marshalling needs them
                data = [Resource._from_son(r) for r in result.get("data", [])]
                return result["total"], data

            # sanity: the endpoint must really return at most page_size items
            resp = endpoint()
            assert len(resp.json["data"]) == min(10, n)
            assert resp.json["total"] == n
            agg_total, agg_data = aggregate()
            assert agg_total == n
            assert len(agg_data) == min(10, n)

            t_only = _timeit(fetch_only)
            t_deser = _timeit(fetch_deser)
            t_excl = _timeit(fetch_excluded)
            t_endpoint = _timeit(endpoint)
            t_agg = _timeit(aggregate)

            print(
                f"{n:>6} | {t_only:>9.2f}ms | {t_deser:>9.2f}ms | {t_excl:>7.2f}ms | "
                f"{t_endpoint:>7.2f}ms | {t_agg:>8.2f}ms || {t_deser - t_only:>6.2f}ms | "
                f"{t_only - t_excl:>5.2f}ms | {t_endpoint - t_deser:>5.2f}ms"
            )
