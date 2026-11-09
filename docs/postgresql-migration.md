# Migrating udata from MongoDB to PostgreSQL

Status: exploratory study, nothing implemented.

## Summary

The switch is feasible but touches most of the codebase. The data itself is
relational at heart and maps well to PostgreSQL. The cost is in the code, which
is written against MongoEngine and its embedded documents.

## Motivation

- **One source of truth with the crawler.** The resources crawler (Hydra) already runs on
  PostgreSQL. Today it keeps its own copy of the resources, fed by udata over HTTP, and writes
  its results back through the udata API. Sharing one PostgreSQL database removes that
  duplication. This is a later phase (see [Phase 2](#phase-2-sharing-the-database-with-hydra)).
- **Less operations work.** A single database engine to run, back up, monitor and upgrade,
  instead of both MongoDB and PostgreSQL.
- **Industry standard.** PostgreSQL is community-governed, under a permissive open source
  license, and supported by every hosting provider and tool. MongoDB is distributed under the
  SSPL, which is not an OSI-approved open source license, and has been dropped by several Linux
  distributions. Its ecosystem in Python (MongoEngine) is smaller than SQLAlchemy's.

## Scope (measured on the repository, excluding tests and migrations)

| Item | Count | Why it matters |
|---|---|---|
| Files touching the database | ~215 | Most of the business code |
| `Document` classes (collections) | 36 | Each becomes a SQLAlchemy model |
| `EmbeddedDocument` classes | 45 | Nested data, no direct column equivalent |
| `.objects(...)` calls | 316 | MongoEngine query syntax to rewrite |
| `ReferenceField` | 92 | Become foreign keys |
| Generic references | 57 | Polymorphic (activity, discussion, notification subjects), no simple foreign key |
| `Q()`, `__raw__`, `$set`/`$push`/`$pull`, `push__`/`pull__` | ~70 | Atomic list updates specific to Mongo |
| `aggregate` pipelines | ~10 | To rewrite in SQL |
| MongoEngine signals | many | Indexing, spam, activity and notifications rely on them |
| `udata/mongo/` custom fields | ~1000 lines | Slug, tag list, extras, URL, encrypted fields |
| `udata/api_fields.py` | ~1500 lines | Generates the Flask-RESTX API models from the MongoEngine fields |
| Mongo-bound dependencies | 3 | `MongoEngineUserDatastore` (`udata/core/user/models.py`), custom Celery beat scheduler (`udata/core/jobs/scheduler.py`), pymongo |
| Vendored `udata/flask_mongoengine/` | 8 modules | Connection, pagination and the WTForms `ModelForm` / `ModelSelectField` used by `udata/forms/` |
| Test files | 172 | factory_boy factories and fixtures |

External constraints:
- **Keep ObjectId identifiers** (24 hex characters) as `CHAR(24)` primary keys. They appear
  in URLs, `/api/1`, `/api/2`, cdata and harvesters.
- **Keep the API contract unchanged.**

## Decisions

- **Stack**: SQLAlchemy 2 + Flask-SQLAlchemy, Alembic, psycopg 3 (see [Stack](#stack)).
- **Rewrite the models.** No compatibility layer that mimics `Dataset.objects(...)`.
- **Migrate everything at once, roll out environment by environment.** All the code moves to
  PostgreSQL together. MongoDB and PostgreSQL then coexist in time, in each environment (dev,
  demo, production), rather than collection by collection (see [Migration timeline](#migration-timeline)).
- **No Mongo migration history in PostgreSQL.** The data is copied from an up-to-date Mongo
  database. `udata/migrations/` keeps running while Mongo is written, and is removed with it.
  Alembic starts from a single initial revision, and `udata db migrate` / `udata db status`
  run both while they coexist.
- **Search is delegated to Elasticsearch wherever possible** (see below). Private or
  permission-bound searches stay in PostgreSQL, and the Elasticsearch index stays fully public.

## Stack

| Layer | Choice | Replaces |
|---|---|---|
| ORM | SQLAlchemy 2 | MongoEngine |
| Flask integration | Flask-SQLAlchemy | `udata/mongo/engine.py`, the vendored `flask_mongoengine` |
| Schema migrations | Alembic | `udata/migrations/` and `udata db migrate` |
| Driver | psycopg 3 | pymongo |
| Forms | wtforms-sqlalchemy | `udata/flask_mongoengine/model_form.py`, `ModelSelectField` |

**SQLAlchemy 2** is the reference ORM in Python and the only one that fits udata's existing
dependencies:
- Flask-Security has a `SQLAlchemyUserDatastore` that replaces `MongoEngineUserDatastore`.
- Authlib ships SQLAlchemy mixins for OAuth2 clients, tokens and codes.
- factory_boy has a `SQLAlchemyModelFactory`, so the test factories keep their shape.

It covers the PostgreSQL features the target schema needs: `JSONB`, arrays, `CHECK`
constraints, partial indexes and `INSERT … ON CONFLICT`. The 2.0 style (`Mapped[...]`,
`mapped_column`) gives typed models that pyright and mypy can check. Relationship loading is
configurable (`selectinload`, `joinedload`) to avoid N+1 queries, and SQLAlchemy Core (SQL
built in Python, without ORM objects) serves the hot paths: metrics, bulk operations and the
backfill.

**Alembic** is maintained by the SQLAlchemy authors. It autogenerates schema migrations from
the models (reviewed by hand), checks for drift (`alembic check`) and supports branches.
`udata db migrate` and `udata db status` wrap it. Large data clean-ups stay in dedicated
scripts rather than Alembic revisions, so they do not block deployments.

**psycopg 3** is the current PostgreSQL driver from the psycopg maintainers, psycopg2 being in
maintenance mode. It supports server-side parameter binding, `COPY` for fast bulk loading (the
backfill), a connection pool (`psycopg_pool`) and `LISTEN/NOTIFY`.

The validation of `JSONB` columns and `extras` is ported from `udata/mongo/`. The API layer
stays on Flask-RESTX.

Alternatives considered:
- **ORM**: the Django ORM is tied to Django. Peewee and Pony have smaller ecosystems and
  fewer PostgreSQL features. SQLModel is built on SQLAlchemy and lags behind it on advanced
  features. Tortoise and Piccolo are async-only, while udata is synchronous (Flask, Celery).
  Raw psycopg would mean rewriting by hand what the ORM provides, for 36 models.
- **Migrations**: Flask-Migrate is only an Alembic wrapper, and udata has its own CLI.
  yoyo-migrations, Sqitch, dbmate and Atlas do not generate migrations from the models.
  pgroll (zero-downtime PostgreSQL migrations) can complement Alembic for large production
  tables.
- **Driver**: asyncpg is async-only.

## Schema mapping

One table per collection. The content changes shape:

| Mongo structure | Examples | PostgreSQL |
|---|---|---|
| Scalar fields | title, slug, dates, flags, enums | Columns |
| `ReferenceField` | `owner`, `organization`, `license` | Foreign keys; the "user or organization, not both" ownership rule becomes a `CHECK` constraint |
| List of references | `Reuse.datasets`, `Dataservice.datasets` | Association tables (`reuse_dataset`, …) |
| List of embedded documents | `Dataset.resources`, `Organization.members`, discussion messages, badges | Child tables (`dataset_resource`, `organization_member`, `discussion_message`) with a `position` column to keep the order |
| Tags | `tags` | `tag` table + association tables |
| Free-form dictionaries | `extras`, `ext`, `harvest`, `quality_cached`, site blocks | `JSONB` |
| `metrics` | `metrics.views`, `metrics.reuses` | `JSONB`, or columns where they are sorted on |
| Generic references | activity, discussion, notification subjects | `(subject_type, subject_id)` columns, no foreign key, integrity checked by the application |
| `_cls` inheritance | activities | Single table with a type column |

Roughly 80% of the schema maps almost as is, 15% moves to child tables without losing any
information, and 5% goes to `JSONB` or polymorphic references.

### Example: `Discussion`

Before: MongoEngine, abridged from `udata/core/discussions/models.py`. A discussion is a single
document: its messages are embedded, and `subject` stores `{"_cls": "Dataset", "_ref": ObjectId(...)}`.

```python
class Message(SpamMixin, EmbeddedDocument):
    id = field(AutoUUIDField(), readonly=True)
    content = field(StringField(required=True, max_length=COMMENT_SIZE_LIMIT))
    posted_on = field(DateTimeField(default=lambda: datetime.now(UTC), required=True),
                      readonly=True)
    posted_by = field(ReferenceField("User"), readonly=True, allow_null=True)


class Discussion(SpamMixin, Linkable, Document):
    user = field(ReferenceField("User"), readonly=True, allow_null=True)
    subject = field(GenericReferenceField(choices=DISCUSSION_SUBJECTS, required=True))
    title = field(StringField(required=True), sortable=True)
    discussion = field(ListField(EmbeddedDocumentField(Message)), readonly=True)
    created = field(DateTimeField(default=lambda: datetime.now(UTC), required=True),
                    readonly=True, sortable=True)
    closed = field(DateTimeField(), readonly=True, sortable=True, allow_null=True)
    extras = field(ExtrasField({"notification": NotificationExtra}))

    meta = {
        "indexes": [
            {"fields": ["$title", "$discussion.content"], "default_language": "french",
             "weights": {"title": 10, "discussion.content": 5}},
            "user", "subject", "-created",
        ],
        "ordering": ["-created"],
    }
```

After: SQLAlchemy 2. Messages move to their own table, references become foreign keys, the
generic subject becomes two columns, and `extras` becomes `JSONB`.

```python
class Message(SpamMixin, Base):
    __tablename__ = "discussion_message"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4,
                                          info=api(readonly=True))
    discussion_id: Mapped[str] = mapped_column(
        ForeignKey("discussion.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    content: Mapped[str] = mapped_column(String(COMMENT_SIZE_LIMIT))
    posted_on: Mapped[datetime] = mapped_column(default=utcnow, info=api(readonly=True))
    posted_by_id: Mapped[str | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    posted_by: Mapped["User | None"] = relationship(info=api(readonly=True))


class Discussion(SpamMixin, Linkable, GenericSubjectMixin, Base):
    __tablename__ = "discussion"

    id: Mapped[str] = mapped_column(CHAR(24), primary_key=True, default=new_object_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(info=api(sortable=True))
    created: Mapped[datetime] = mapped_column(default=utcnow, info=api(readonly=True, sortable=True))
    closed: Mapped[datetime | None] = mapped_column(info=api(readonly=True, sortable=True))
    extras: Mapped[dict] = mapped_column(JSONB, default=dict)

    # keeps the "discussion" name so the API JSON does not change
    discussion: Mapped[list[Message]] = relationship(
        order_by=Message.position, cascade="all, delete-orphan", info=api(readonly=True))

    __table_args__ = (Index("ix_discussion_subject", "subject_type", "subject_id"),)
```

`api(...)`, `new_object_id` and `GenericSubjectMixin` do not exist yet. Field metadata
currently passed to `field(...)` (readonly, description, sortable, checks) moves to
`mapped_column(info=...)`, and `generate_fields` in `udata/api_fields.py` is rewritten to
read the SQLAlchemy mapper. This is what keeps the API contract identical.

## Search

Today, MongoDB serves search on its own in three ways:
- **Text indexes** on 11 models, used by the `?q=` list endpoints (`core/dataset/api.py`,
  `api_fields.py` for `searchable=True` models). They are also used by `mongo_search`, the
  fallback of the search endpoints when `ELASTICSEARCH_URL` is empty (`search/query.py`),
  which is the default in development and tests.
- **`__icontains` substring searches** (unindexed regexes): `/suggest/` endpoints, tags, geo
  zones, user dashboard filters, organization members.
- **`$regexMatch`** to filter a dataset's resources by title (`core/dataset/apiv2.py`).

Target:
- **Elasticsearch only** for the search endpoints, public `?q=` lists and autocomplete
  (`search_as_you_type`). New indexes for tags, geo zones and, if needed, harvest sources,
  charts and topic elements. `mongo_search` and the fallback are removed: Elasticsearch becomes
  a required dependency, including for development and tests.
- **PostgreSQL (`ILIKE` + `pg_trgm`)** for searches over private or permission-bound content:
  the existing 7 adapters only index public content (`is_indexable`). This covers the user
  dashboard, organization members, admin user search by email and the resource filter.
- Indexing hooks (`search/__init__.py`) move to after-commit events. `udata search index`
  rebuilds the index when an environment switches its reads to PostgreSQL.

## Migration timeline

All the code moves to PostgreSQL at once, then the switch is rolled out environment by
environment: dev, demo, production. MongoDB is decommissioned in the same order. Both databases
coexist in time in each environment, with tests at every step. The timeline is given as stages
with exit criteria, not dates.

Moving collection by collection was considered and left out: during the transition, part of
the data would live in Mongo and part in PostgreSQL. References would have to be resolved
across both stores in Python, foreign keys postponed, and every combination of migrated
collections tested.

### States of an environment

Each environment goes through the same four states, set by one setting (for example
`DATABASE_MODE`):

| State | Writes | Reads | Rollback |
|---|---|---|---|
| *Mongo* | Mongo | Mongo | — |
| *Shadow* | Both, after a backfill | Mongo, with PostgreSQL reads compared in the background | Stop writing to PostgreSQL |
| *PostgreSQL primary* | Both | PostgreSQL | Switch the setting back to *Shadow* |
| *PostgreSQL only* | PostgreSQL | PostgreSQL | Restore from backup |

- At any time, all reads come from a single store, so there are no references across stores
  and the PostgreSQL schema has its foreign keys from the start.
- Writes to both stores are not atomic: a reconciliation job compares them and repairs drift.
- Since both stores hold all the data in *Shadow* and *PostgreSQL primary*, reads can be
  switched module by module as a precaution, without cross-store references. This is an
  option, not a requirement.
- An environment moves to the next state only when its exit criteria are met.

### Stage 0: foundations, on `main`, still on Mongo

Shipped continuously, to avoid a long-lived branch that conflicts with ongoing work:

- Isolate persistence: move the 316 `.objects(...)` calls behind per-module functions. This is
  the bulk of the work, and it needs no PostgreSQL.
- Delegate search to Elasticsearch (see [Search](#search)), which removes the dependency on
  Mongo text indexes.
- Add PostgreSQL to `docker-compose.yml`, CI and every environment; set up SQLAlchemy 2,
  Alembic and psycopg 3 next to MongoEngine.
- Write the target schema from the inventory (fields, embedded documents, indexes, queries per
  collection), reviewed by the team.

Exit: no `.objects(...)` call outside the persistence layer, search served by Elasticsearch.

### Stage 1: rewrite

- Rewrite all models in SQLAlchemy 2 and the persistence layer on top of them. Port
  `udata/mongo/` fields, mixins (`Owned`, `WithMetrics`, `Auditable`, `SpamMixin`,
  `Linkable`), signals as session events, `generate_fields` in `udata/api_fields.py`, the
  forms, the Flask-Security datastore, the Authlib models and the Celery scheduler.
- Generate the initial Alembic revision and review it by hand.
- Build the migration tooling: backfill (`COPY` through psycopg 3), writes to both stores,
  background read comparison, reconciliation job.
- The code reaches `main` behind `DATABASE_MODE`, with *Mongo* as the default.

Exit: the test suite passes in every state, locally and in CI.

### Stage 2: dev

- Backfill, then *Shadow*, then *PostgreSQL primary*.
- Run cdata end to end and the API response comparison.
- Rehearse the rollback from *PostgreSQL primary* to *Shadow*.

Exit: no differences reported, rollback works.

### Stage 3: demo

Same steps as dev. If demo does not have production's data volume, also backfill a
production copy to measure the backfill time and query performance.

Exit: no differences reported, rollback works, acceptable backfill time.

### Stage 4: production

1. **Backfill, then *Shadow*: testing in production without user impact.** Mongo still serves
   every request. Real writes go to both stores and real reads are compared in the background,
   which also measures PostgreSQL under real load.
   Exit: no differences over an agreed period, acceptable query times.
2. ***PostgreSQL primary*.** Users are served by PostgreSQL, Mongo is still written, and rollback
   is a setting change. Reads can be switched gradually first: admin and internal requests,
   then a share of the traffic, or module by module.
   Exit: no differences and no incident over an agreed period.

### Stage 5: decommission MongoDB

In dev, then demo, then production, testing after each one:

1. Switch to *PostgreSQL only* after a final Mongo backup, kept archived.
2. Once all environments are *PostgreSQL only*, remove MongoEngine, pymongo, `udata/mongo/`,
   `udata/flask_mongoengine/`, `udata/migrations/` and the migration tooling from the code.
3. Remove MongoDB from `docker-compose.yml`, CI and each environment.

## Phase 2: sharing the database with Hydra

Out of scope of this plan. During phase 1, the integration with the crawler stays as it is,
in both directions:
- udata notifies Hydra of every resource change over HTTP (Celery task in
  `udata/core/dataset/events.py`);
- Hydra writes its results back into the resource extras (`check:*`, `analysis:*`) through the
  udata API, so `Dataset.update_resource_extras` is ported as a targeted `UPDATE`.

Once an environment is *PostgreSQL primary*, phase 2 can start. It will have its own plan, and
mostly changes the Hydra codebase:
- Hydra reads the catalog directly from the shared PostgreSQL database instead of keeping its
  own copy, so udata stops notifying Hydra of resource changes;
- Hydra stops sending its results to udata through the API.

## Performance

Neither database is faster in general. For udata:
- Mongo is slightly ahead for reading a whole dataset with its resources (one read, no join).
- PostgreSQL wins for updating one resource (Mongo rewrites the whole dataset document),
  aggregations and metrics, ad hoc analysis, and indexed substring search.
- Data volume is modest for both.

The database is probably not udata's bottleneck: search goes through Elasticsearch, public
pages are cached, and time is likely spent in Python (serialization, N+1 queries, signals).
Profile before deciding: the Mongo profiler on a production copy, then the most-called API
endpoints. The main gains are data integrity, easier analysis and simpler aggregation code.

## Verification

- The full pytest suite passes on PostgreSQL with `SQLAlchemyModelFactory` factories.
- `alembic upgrade head` on an empty database, then `alembic check`: no drift between models
  and schema.
- The test suite passes in each state (*Mongo*, *Shadow*, *PostgreSQL primary*, *PostgreSQL only*).
- In each environment, before each state change: row count per table matches the document
  count per collection, and the background read comparison and the reconciliation job report
  no differences.
- JSON responses from a sample of `/api/1` and `/api/2` URLs are identical whichever store
  serves the reads. `?q=` result ordering may differ slightly.
- The rollback from *PostgreSQL primary* to *Shadow* is rehearsed in dev and demo.
- cdata runs end to end in each environment.
