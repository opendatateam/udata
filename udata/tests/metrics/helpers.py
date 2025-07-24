from datetime import datetime, timedelta


def chunks(xs, n):
    return [xs[i : i + n] for i in range(0, len(xs), n)]


def mock_metrics_api(app, rmock, endpoint, value_keys, values, page_size: int = 50):
    for i, value in enumerate(values):
        value["__id"] = i

    chunked = list(chunks(values, page_size))

    for value_key in value_keys:
        next = None
        for i, chunk in enumerate(chunked):
            page_number = i + 1

            if next is None:
                url = f"{app.config['METRICS_API']}/{endpoint}_total/data/?{value_key}__greater=1&page_size={page_size}"
            else:
                url = next

            # Test if we're on the last page
            if page_number == len(chunked):
                next = None
            else:
                next = f"{app.config['METRICS_API']}/{endpoint}_total/data/?{value_key}__greater=1&page={page_number + 1}&page_size={page_size}"

            rmock.get(
                url, json={"data": chunk, "links": {"next": next}, "meta": {"total": len(values)}}
            )


def mock_monthly_metrics_payload(app, rmock, target, data, target_id="id", url=None):
    if not url:
        url = (
            f"{app.config['METRICS_API']}/{target}s/data/"
            + f"?metric_month__sort=desc&{target}_id__exact={target_id}"
        )
    current_month = datetime.now().strftime("%Y-%m")
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    rmock.get(
        url,
        json={
            "data": [
                {
                    "metric_month": current_month,
                    **{f"monthly_{key}": len(key) * value + 1 for key, value in data},
                },
                {
                    "metric_month": last_month,
                    **{f"monthly_{key}": len(key) * value for key, value in data},
                },
            ],
            "meta": {"total": 2},
        },
    )
