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
  duplication. This is phase 2 (see [Phase 2: sharing the database with the crawler](#phase-2-sharing-the-database-with-the-crawler)).
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
- **No Mongo migration history.** The 76 scripts in `udata/migrations/` are dropped. The data
  migration starts from an up-to-date Mongo database (`udata db status` shows nothing pending).
  Alembic starts from a single initial revision, and `udata db migrate` / `udata db status`
  wrap Alembic.
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
| Validation of `JSONB` contents | Pydantic | `EmbeddedDocument` validation |

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
ETL.

**Alembic** is maintained by the SQLAlchemy authors. It autogenerates schema migrations from
the models (reviewed by hand), checks for drift (`alembic check`) and supports branches.
`udata db migrate` and `udata db status` wrap it. Large data clean-ups stay in dedicated
scripts rather than Alembic revisions, so they do not block deployments.

**psycopg 3** is the current PostgreSQL driver from the psycopg maintainers, psycopg2 being in
maintenance mode. It supports server-side parameter binding, `COPY` for fast bulk loading (the
ETL), a connection pool (`psycopg_pool`) and `LISTEN/NOTIFY`, which phase 2 needs for the
outbox notifications.

**Pydantic** validates the contents of the `JSONB` columns (`checksum`, `schema`, `spatial`,
`harvest`…) through a small SQLAlchemy `TypeDecorator`. PostgreSQL accepts any JSON in these
columns, so without it the validation `EmbeddedDocument` provides today would be lost. In
phase 2, it also defines the event payloads shared with Hydra. The API layer stays on
Flask-RESTX during the migration; moving it to Pydantic would be a separate project.

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
  rebuilds the index after the data migration.

## Phase 2: sharing the database with the crawler

Phase 1 (everything above and the [Approach](#approach)) moves udata to PostgreSQL and leaves the
Hydra integration as it is: same HTTP calls in both directions, same reserved extras. Phase 2
starts once udata runs on PostgreSQL in production.

Today (`udata/core/dataset/events.py`, `udata/core/dataset/models.py`):
- **udata → Hydra**: on `on_resource_added` / `on_resource_updated` / `on_resource_removed`, a
  Celery task sends the serialized resource to `RESOURCES_ANALYSER_URI/api/resources/`
  (POST/PUT/DELETE) when `PUBLISH_ON_RESOURCE_EVENTS` is enabled.
- **Hydra → udata**: Hydra writes its results into the reserved resource extras (`check:*`,
  `analysis:*`) through the udata API. `Dataset.update_resource_extras` exists only because this
  path rewrites the whole dataset document on datasets with 15k+ resources.

Phase 2 target, in one PostgreSQL database:
- **One schema per application** (`udata`, `hydra`) and one role per application. udata owns
  `dataset_resource` and the rest of the catalog; Hydra gets read-only access to the tables it
  needs. Hydra owns its result tables (checks, analysis); udata gets read-only access to them.
  Each application keeps its own migrations for its own schema.
- **No more duplicated resource list in Hydra**: it reads `udata.dataset_resource` directly.
- **Results stay in Hydra's tables** instead of being copied into resource extras. udata reads
  them with a join (or a view) and keeps exposing them as `check:*` / `analysis:*` extras in
  the API, so the API contract does not change. The `update_resource_extras` hot path goes away.
- **Notifications through the database** with a transactional outbox: each application inserts
  an event row (`resource.created`, `resource.modified`, `resource.deleted`,
  `check.completed`…) in the same transaction as the change, and sends a `pg_notify` to wake up
  the other side. The outbox table is the durable record: a listener that was down catches up
  from it, since `LISTEN/NOTIFY` alone loses messages sent while nobody listens. This replaces
  the HTTP calls and the Celery `publish` task in both directions.
- **udata reacts to Hydra events** to do what the API callback did: reindex the dataset in
  Elasticsearch and invalidate caches.

Points of attention:
- Never let both applications write the same table: writes from Hydra would bypass udata's
  validation, signals and search indexing.
- Cross-schema foreign keys (`hydra.check.resource_id` → `udata.dataset_resource.id`) give
  integrity but couple the two applications' schema changes; agree on which tables are a
  shared contract.
- The crawler's write load lands on the same server as the web application: size the
  instance, use a connection pooler (PgBouncer) and watch for long transactions.

## Approach

Phase 1, udata only. The Hydra integration is left unchanged: `udata/core/dataset/events.py`
keeps sending resource events over HTTP, and Hydra keeps writing its results through the API,
so `update_resource_extras` is ported as a targeted `UPDATE` on `dataset_resource`.

1. **Inventory**: fields, embedded documents, indexes and queries per collection, then a
   target schema reviewed by the team.
2. **Isolate persistence while still on Mongo**: move the 316 `.objects(...)` calls behind
   per-module functions, shipped and tested step by step. This is the bulk of the work and
   de-risks the rest.
3. **Rewrite the models in SQLAlchemy 2**: port `udata/mongo/` fields, mixins (`Owned`,
   `WithMetrics`, `Auditable`, `SpamMixin`, `Linkable`), signals (session events) and
   `api_fields.py`. Autogenerate the initial Alembic revision and review it by hand.
4. **Switch module by module** behind the layer from step 2, from leaves (licenses, geo
   zones, posts, contact points) to the core (user, organization, dataset). Replace the
   Flask-Security datastore and adapt the Celery scheduler.
5. **Migrate the data** with an ETL script: keep the ObjectIds, flatten the embedded
   documents, wire the references. Run it locally, then on a production copy.
6. **Production cutover** during a short `READ_ONLY_MODE` window (the flag exists),
   or with temporary dual writes if no downtime is acceptable.

Redis and file storage are not affected.

Phase 2, with Hydra (see [Phase 2](#phase-2-sharing-the-database-with-the-crawler)):

1. Create the `hydra` schema and the per-application roles.
2. Point Hydra at `udata.dataset_resource` and drop its own copy of the resources.
3. Move Hydra's results to its own tables, read by udata and exposed as the same extras.
4. Replace the HTTP calls and the Celery `publish` task with the outbox, in both directions.

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
- Row count per table matches the document count per collection after the ETL.
- JSON responses from a sample of `/api/1` and `/api/2` URLs are identical on both backends
  loaded with the same data. `?q=` result ordering may differ slightly.
- cdata runs end to end against the PostgreSQL instance.
