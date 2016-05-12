# Changelog

## Breaking Changes

* 2016-05-11: Upgrade of ElasticSearch from 1.7 to 2.3 [#449](https://github.com/etalab/udata/pull/449)

You have to re-initialize the index from scratch, not just use the `reindex` command given that ElasticSearch 2+ doesn't provide a way to [delete mappings](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-delete-mapping.html) anymore. The command is `udata search init` and may take some time given the amount of data you are dealing with.

## New & Improved

* 2016-05-12: Add fields masks to reduce API payloads [#451](https://github.com/etalab/udata/pull/451)

The addition of [fields masks](http://flask-restplus.readthedocs.io/en/stable/mask.html) in Flask-RESTPlus allows us to reduce the retrieved payload within the admin — especially for datasets — and results in a performances boost.
