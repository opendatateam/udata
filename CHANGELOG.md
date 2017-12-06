# Changelog

## Current (in progress)

- Fix flask_security celery tasks context [#1249](https://github.com/opendatateam/udata/pull/1249)
- Fix `dataset.quality` handling when no format filled [#1265](https://github.com/opendatateam/udata/pull/1265)
- Ignore celery tasks results except for tasks which require it and lower the default results expiration to 6 hours [#1281](https://github.com/opendatateam/udata/pull/1281)
- Import community resource avatar style from udata-gouvfr [#1288](https://github.com/opendatateam/udata/pull/1288)
- Terms are now handled from markdown and customizable with the `SITE_TERMS_LOCATION` setting. [#1285](https://github.com/opendatateam/udata/pull/1285)
- Deeplink to resource [#1289](https://github.com/opendatateam/udata/pull/1289)

## 1.2.3 (2017-10-27)

- Check only the uncollapsed resources at first on dataset view [#1246](https://github.com/opendatateam/udata/pull/1246)

## 1.2.2 (2017-10-26)

- Fixes on the `search index command` [#1245](https://github.com/opendatateam/udata/pull/1245)

## 1.2.1 (2017-10-26)

- Introduce `udata search index` commmand to replace both deprecated `udata search init` and `udata search reindex` commands. They will be removed in udata 1.4. [#1233](https://github.com/opendatateam/udata/pull/1233)
- Rollback oauthlib from 2.0.5 to 2.0.2, pending a permanent solution [#1237](https://github.com/opendatateam/udata/pull/1237)
- Get cached linkchecker result before hitting API [#1235](https://github.com/opendatateam/udata/pull/1235)
- Cleanup resources checksum (migration) [#1239](https://github.com/opendatateam/udata/pull/1239)
- Show check results in resource modal [#1242](https://github.com/opendatateam/udata/pull/1242)
- Cache avatar rendering [#1243](https://github.com/opendatateam/udata/pull/1243)

## 1.2.0 (2017-10-20)

### New features and big improvements

- Expose harvester scheduling through the API and the admin interface [#1123](https://github.com/opendatateam/udata/pull/1123)
- Added a `udata info` command for diagnostic purpose [#1179](https://github.com/opendatateam/udata/pull/1179)
- Switch from static theme avatars/placeholders to [identicons](https://en.wikipedia.org/wiki/Identicon) for readability (mostly on discussions) [#1193](https://github.com/opendatateam/udata/pull/1193)
- Move croquemort features to a generic link checker architecture [#1110](https://github.com/opendatateam/udata/pull/1110)
- CKAN and OpenDataSoft backends are now optionnal separate udata extensions [#1213](https://github.com/opendatateam/udata/pull/1213)
- Better search autocomplete [#1222](https://github.com/opendatateam/udata/pull/1222)
- Big post improvements (discussions support, navigation, fixes...) [#1224](https://github.com/opendatateam/udata/pull/1224)

### Breaking changes

- Upgrade to Celery 4.1.0. All celery parameters should be updated. (See [Celery options documentation](https://udata.readthedocs.io/en/stable/adapting-settings/#celery-options) [#1150](https://github.com/opendatateam/udata/pull/1050)
- Switch to [Crowdin](https://crowdin.com) to manage translations [#1171](https://github.com/opendatateam/udata/pull/1171)
- Switch to `Flask-Security`. `Flask-Security-Fork` should be uninstalled before installing the new requirements [#958](https://github.com/opendatateam/udata/pull/958)

### Miscellaneous changes and fixes

- Display organization metrics in the organization page tab labels [#1022](https://github.com/opendatateam/udata/pull/1022)
- Organization dashboard page has been merged into the main organization page [#1023](https://github.com/opendatateam/udata/pull/1023)
- Fix an issue causing a loss of data input at the global search input level [#1019](https://github.com/opendatateam/udata/pull/1019)
- Fixes a lot of encoding issues [#1146](https://github.com/opendatateam/udata/pull/1146)
- Add `.ttl` and `.n3` as supported file extensions [#1183](https://github.com/opendatateam/udata/pull/1183)
- Improve logging for adhoc scripts [#1184](https://github.com/opendatateam/udata/pull/1184)
- Improve URLs validation (support new tlds, unicode URLs...) [#1182](https://github.com/opendatateam/udata/pull/1182)
- Properly serialize empty geometries for zones missing it and prevent leaflet crash on invalid bounds [#1188](https://github.com/opendatateam/udata/pull/1188)
- Start validating some configuration parameters [#1197](https://github.com/opendatateam/udata/pull/1197)
- Remove resources without title or url [migration] [#1200](https://github.com/opendatateam/udata/pull/1200)
- Improve harvesting licenses detection [#1203](https://github.com/opendatateam/udata/pull/1203)
- Added missing delete post and topic admin actions [#1202](https://github.com/opendatateam/udata/pull/1202)
- Fix the scroll to a discussion sub-thread [#1206](https://github.com/opendatateam/udata/pull/1206)
- Fix duplication in discussions [migration] [#1209](https://github.com/opendatateam/udata/pull/1209)
- Display that a discussion has been closed [#1216](https://github.com/opendatateam/udata/pull/1216)
- Explicit dataset search reuse facet context (only known reuses) [#1219](https://github.com/opendatateam/udata/pull/1219)
- Optimize indexation a little bit [#1215](https://github.com/opendatateam/udata/pull/1215)
- Fix some reversed temporal coverage [migration] [#1214](https://github.com/opendatateam/udata/pull/1214)


## 1.1.8 (2017-09-28)

- Display membership modal actions buttons for site administrators and on membership display. [#1176](https://github.com/opendatateam/udata/pull/1176)
- Fix organization avatar in admin profile [#1175](https://github.com/opendatateam/udata/issues/1175)

## 1.1.7 (2017-09-25)

- Prevent a random territory from being displayed when query doesn't match [#1124](https://github.com/opendatateam/udata/pull/1124)
- Display avatar when the community resource owner is an organization [#1125](https://github.com/opendatateam/udata/pull/1125)
- Refactor the "publish as" screen to make it more obvious that an user is publishing under its own name [#1122](https://github.com/opendatateam/udata/pull/1122)
- Make the "find your organization" screen cards clickable (send to the organization page) [#1129](https://github.com/opendatateam/udata/pull/1129)
- Fix "Center the full picture" on user avatar upload [#1130](https://github.com/opendatateam/udata/issues/1130)
- Hide issue modal forbidden actions [#1128](https://github.com/opendatateam/udata/pull/1128)
- Ensure spatial coverage zones are resolved when submitted from the API or when querying oembed API. [#1140](https://github.com/opendatateam/udata/pull/1140)
- Prevent user metrics computation when the object owner is an organization (and vice versa) [#1152](https://github.com/opendatateam/udata/pull/1152)

## 1.1.6 (2017-09-11)

- Fix CircleCI automated publication on release tags
  [#1120](https://github.com/opendatateam/udata/pull/1120)

## 1.1.5 (2017-09-11)

- Fix the organization members grid in admin
  [#934](https://github.com/opendatateam/udata/issues/934)
- Fix and tune harvest admin loading state and payload size
  [#1113](https://github.com/opendatateam/udata/issues/1113)
- Automatically schedule validated harvesters and allow to (re)schedule them
  [#1114](https://github.com/opendatateam/udata/pull/1114)
- Raise the minimum `raven` version to ensure sentry is filtering legit HTTP exceptions
  [#774](https://github.com/opendatateam/udata/issues/774)
- Pin GeoJSON version to avoid breaking changes
  [#1118](https://github.com/opendatateam/udata/pull/1118)
- Deduplicate organization members
  [#1111](https://github.com/opendatateam/udata/issues/1111)

## 1.1.4 (2017-09-05)

- Fix packaging

## 1.1.3 (2017-09-05)

- Make the spatial search levels exclusion list configurable through `SPATIAL_SEARCH_EXCLUDE_LEVELS`.
  [#1101](https://github.com/opendatateam/udata/pull/1101)
- Fix facets labelizer with html handling
  [#1102](https://github.com/opendatateam/udata/issues/1102)
- Ensure territories pages have image defined in metadatas
  [#1103](https://github.com/opendatateam/udata/issues/1103)
- Strip tags in autocomplete results
  [#1104](https://github.com/opendatateam/udata/pull/1104)
- Transmit link checker status to frontend
  [#1048](https://github.com/opendatateam/udata/issues/1048)
- Remove plus signs from search query
  [#1048](https://github.com/opendatateam/udata/issues/987)

## 1.1.2 (2017-09-04)

- Handle territory URLs generation without validity
  [#1068](https://github.com/opendatateam/udata/issues/1068)
- Added a contact button to trigger discussions
  [#1076](https://github.com/opendatateam/udata/pull/1076)
- Improve harvest error handling
  [#1078](https://github.com/opendatateam/udata/pull/1078)
- Improve elasticsearch configurability
  [#1096](https://github.com/opendatateam/udata/pull/1096)
- Lots of fixes admin files upload
  [1094](https://github.com/opendatateam/udata/pull/1094)
- Prevent the "Bad request error" happening on search but only on some servers
  [#1097](https://github.com/opendatateam/udata/pull/1097)
- Migrate spatial granularities to new identifiers
- Migrate remaining legacy spatial identifiers
  [#1080](https://github.com/opendatateam/udata/pull/1080)
- Fix the discussion API documention
  [#1093](https://github.com/opendatateam/udata/pull/1093)

## 1.1.1 (2017-07-31)

- Fix an issue preventing reuse edition:
  [#1027](https://github.com/opendatateam/udata/issues/1027)
- Fix an issue preventing user display and edit in admin:
  [#1030](https://github.com/opendatateam/udata/issues/1030)
- Fix an error when a membership request is accepted:
  [#1028](https://github.com/opendatateam/udata/issues/1028)
- Fix issue modal on a reuse:
  [#1026](https://github.com/opendatateam/udata/issues/1026)
- Fix sort by date on admin users list:
  [#1029](https://github.com/opendatateam/udata/issues/1029)
- Improve the `purge` command
  [#1039](https://github.com/opendatateam/udata/pull/1039)
- Ensure search does not fail when a deleted object has not been
  unindexed yet
  [#1063](https://github.com/opendatateam/udata/issues/1063)
- Start using Celery queues to handle task priorities
  [#1067](https://github.com/opendatateam/udata/pull/1067)
- Updated translations

## 1.1.0 (2017-07-05)

### New features and improvements

- Added a [DCAT](https://www.w3.org/TR/vocab-dcat/) harvester
  and expose metadata as RDF/DCAT.
  [#966](https://github.com/opendatateam/udata/pull/966)
  See the dedicated documentions:

  - [RDF](https://udata.readthedocs.io/en/stable/rdf/)
  - [Harvesting](https://udata.readthedocs.io/en/stable/harvesting/)

- Images are now optimized and you can force rerendering using the `udata images render` command.
- Allowed files extensions are now configurable via the `ALLOWED_RESOURCES_EXTENSIONS` setting
  and both admin and API will have the same behavior
  [#833](https://github.com/opendatateam/udata/pull/833).
- Improve and fix notifications:
  [#928](https://github.com/opendatateam/udata/issues/928)

  - Changed notification style to toast
  - Fix notifications that weren't displayed on form submission
- Add a toggle indicator on dataset quality blocks that are collapsible
  [#915](https://github.com/opendatateam/udata/issues/915)
- Integrating latest versions of GeoZones and GeoLogos for territories.
  Especially using history of towns, counties and regions from GeoHisto.
  [#499](https://github.com/opendatateam/udata/issues/499)

### Breaking Changes

- Themes are now entrypoint-based [#829](https://github.com/opendatateam/udata/pull/829).
  There is also a new [theming documention](https://udata.readthedocs.io/en/stable/creating-theme/).
- Images placeholders are now entirely provided by themes
  [#707](https://github.com/opendatateam/udata/issues/707)
  [#1006](https://github.com/opendatateam/udata/issues/1006)
- Harvester declaration is now entrypoint-based
  [#1004](https://github.com/opendatateam/udata/pull/1004)

### Fixes

- Ensure URLs are stripped [#823](https://github.com/opendatateam/udata/pull/823)
- Lot of fixes and improvements on Harvest admin UI
  [#817](https://github.com/opendatateam/udata/pull/817):

  - harvester edition fixed (and missing API added)
  - harvester deletion fixed
  - harvester listing is now paginated
  - more detailed harvesters widgets
  - ensure harvest source are owned by a user or an organization, not both [migration]

- Pure Vue.js search facets
  [#880](https://github.com/opendatateam/udata/pull/880).
  Improve and fix the datepicker:

  - Proper sizing and positionning in dropdowns
  - Fix initial value not being displayed
  - Make it usable on keyboard
  - Allows to define `min` and `max` values to disable some dates
  - Keyboard input is reflected into the calendar
    [#615](https://github.com/opendatateam/udata/issues/615)
- Disable `next` button when no file has been uploaded
  [#930](https://github.com/opendatateam/udata/issues/930)
- Fix badges notification mails
  [#894](https://github.com/opendatateam/udata/issues/894)
- Fix the `udata search reindex` command
  [#1009](https://github.com/opendatateam/udata/issues/1009)
- Reindex datasets when their parent organization is purged
  [#1008](https://github.com/opendatateam/udata/issues/1008)

### Miscellaneous / Internal

- Upgrade to Flask-Mongoengine 0.9.3, Flask-WTF 0.14.2, mongoengine 0.13.0.
  [#812](https://github.com/opendatateam/udata/pull/812)
  [#871](https://github.com/opendatateam/udata/pull/871)
  [#903](https://github.com/opendatateam/udata/pull/903)
- Upgrade to Flask-Login 0.4.0 and switch from Flask-Security to the latest
  [Flask-Security-Fork](https://pypi.python.org/pypi/Flask-Security-Fork)
  [#813](https://github.com/opendatateam/udata/pull/813)
- Migrated remaining widgets to Vue.js [#828](https://github.com/opendatateam/udata/pull/828):

  - bug fixes on migrated widgets (Issues button/modal, integrate popover, coverage map)
  - more coherent JS environment for developpers
  - lighter assets
  - drop Handlebars dependency

- bleach and html5lib have been updated leading to more secure html/markdown cleanup
  and [better performances](http://bluesock.org/~willkg/blog/dev/bleach_2_0.html)
  [#838](https://github.com/opendatateam/udata/pull/838)
- Drop `jquery-slimscroll` and fix admin menu scrolling
  [#851](https://github.com/opendatateam/udata/pull/851)
- drop jquery.dotdotdot for a lighter css-only solution (less memory consumption)
  [#853](https://github.com/opendatateam/udata/pull/853)
- Lighter style [#869](https://github.com/opendatateam/udata/pull/869):

  - Drop glyphicons and use only Font-Awesome (more coherence, less fonts)
  - lighter bootstrap style by importing only what's needed
  - make use of bootstrap and admin-lte variables (easier for theming)
  - proper separation between front and admin style
- Drop `ExtractTextPlugin` on Vue components style:

  - faster (re)compilation time
  - resolves most compilation and missing style issues
    [#555](https://github.com/opendatateam/udata/issues/555)
    [#710](https://github.com/opendatateam/udata/issues/710)
  - allows use of hot components reloading.
- Pure Vue.js modals. Fix the default membership role. Added contribute modal.
  [#873](https://github.com/opendatateam/udata/pull/873)
- Easier Vue.js development/debugging:

  - Drop `Vue.config.replace = false`: compatible with Vue.js 1/2 and no more style guessing
    [#760](https://github.com/opendatateam/udata/pull/760)
  - `name` on all components: no more `Anonymous Component` in Vue debugger
  - No more `Fragments`
  - More ES6 everywhere
- Make metrics deactivable for tests
  [#905](https://github.com/opendatateam/udata/pull/905)

## 1.0.11 (2017-05-25)

- Fix presubmit form errors handling
  [#909](https://github.com/opendatateam/udata/pull/909)
- Fix producer sidebar image sizing
  [#913](https://github.com/opendatateam/udata/issues/913)
- Fix js `Model.save()` not updating in some cases
  [#910](https://github.com/opendatateam/udata/pull/910)

## 1.0.10 (2017-05-11)

- Fix bad stored (community) resources URLs [migration]
  [#882](https://github.com/opendatateam/udata/issues/882)
- Proper producer logo display on dataset pages
- Fix CKAN harvester empty notes and `metadata` file type handling
- Remove (temporary) badges metrics
  [#885](https://github.com/opendatateam/udata/issues/885)
- Test and fix topic search
  [#892](https://github.com/opendatateam/udata/pull/892)

## 1.0.9 (2017-04-23)

- Fix broken post view
  [#877](https://github.com/opendatateam/udata/pull/877)
- Fix new issue submission
  [#874](https://github.com/opendatateam/udata/issues/874)
- Display full images/logo/avatars URL in references too
  [#824](https://github.com/opendatateam/udata/issues/824)

## 1.0.8 (2017-04-14)

- Allow more headers in cors preflight headers
  [#857](https://github.com/opendatateam/udata/pull/857)
  [#860](https://github.com/opendatateam/udata/pull/860)
- Fix editorialization admin
  [#863](https://github.com/opendatateam/udata/pull/863)
- Fix missing completer images and ensure completion API is usable on a different domain
  [#864](https://github.com/opendatateam/udata/pull/864)

## 1.0.7 (2017-04-07)

- Fix display for zone completer existing values
  [#845](https://github.com/opendatateam/udata/issues/845)
- Proper badge display on dataset and organization page
  [#849](https://github.com/opendatateam/udata/issues/849)
- Remove useless `discussions` from views contexts.
  [#850](https://github.com/opendatateam/udata/pull/850)
- Fix the inline resource edit button not redirecting to admin
  [#852](https://github.com/opendatateam/udata/pull/852)
- Fix broken checksum component
  [#846](https://github.com/opendatateam/udata/issues/846)

## 1.0.6 (2017-04-01)

- Default values are properly displayed on dataset form
  [#745](https://github.com/opendatateam/udata/issues/745)
- Prevent a redirect on discussion fetch
  [#795](https://github.com/opendatateam/udata/issues/795)
- API exposes both original and biggest thumbnail for organization logo, reuse image and user avatar
  [#824](https://github.com/opendatateam/udata/issues/824)
- Restore the broken URL check feature
  [#840](https://github.com/opendatateam/udata/issues/840)
- Temporarily ignore INSPIRE in ODS harvester
  [#837](https://github.com/opendatateam/udata/pull/837)
- Allow `X-API-KEY` and `X-Fields` in cors preflight headers
  [#841](https://github.com/opendatateam/udata/pull/841)

## 1.0.5 (2017-03-27)

- Fixes error display in forms [#830](https://github.com/opendatateam/udata/pull/830)
- Fixes date range picker dates validation [#830](https://github.com/opendatateam/udata/pull/830)
- Fix badges entries not showing in admin [#825](https://github.com/opendatateam/udata/pull/825)

## 1.0.4 (2017-03-01)

- Fix badges trying to use API too early
  [#799](https://github.com/opendatateam/udata/pull/799)
- Some minor tuning on generic references
  [#801](https://github.com/opendatateam/udata/pull/801)
- Cleanup factories
  [#808](https://github.com/opendatateam/udata/pull/808)
- Fix user default metrics not being set [migration]
  [#809](https://github.com/opendatateam/udata/pull/809)
- Fix metric update after transfer
  [#810](https://github.com/opendatateam/udata/pull/810)
- Improve spatial completion ponderation (spatial zones reindexation required)
  [#811](https://github.com/opendatateam/udata/pull/811)

## 1.0.3 (2017-02-21)

- Fix JavaScript locales handling [#786](https://github.com/opendatateam/udata/pull/786)
- Optimize images sizes for territory placeholders [#788](https://github.com/opendatateam/udata/issues/788)
- Restore placeholders in search suggestions, fix [#790](https://github.com/opendatateam/udata/issues/790)
- Fix share popover in production build [#793](https://github.com/opendatateam/udata/pull/793)

## 1.0.2 (2017-02-20)

- Fix assets packaging for production [#763](https://github.com/opendatateam/udata/pull/763) [#765](https://github.com/opendatateam/udata/pull/765)
- Transform `udata_version` jinja global into a reusable (by themes) `package_version` [#768](https://github.com/opendatateam/udata/pull/768)
- Ensure topics datasets and reuses can display event with a topic parameter [#769](https://github.com/opendatateam/udata/pull/769)
- Raise a `400 Bad Request` when a bad `class` attribute is provided to the API
  (for entry point not using forms). [#772](https://github.com/opendatateam/udata/issues/772)
- Fix datasets with spatial coverage not being indexed [#778](https://github.com/opendatateam/udata/issues/778)
- Ensure theme assets cache is versionned (and flushed when necessary)
  [#781](https://github.com/opendatateam/udata/pull/781)
- Raise maximum tag length to 96 in order to at least support
  [official INSPIRE tags](http://inspire.ec.europa.eu/theme)
  [#782](https://github.com/opendatateam/udata/pull/782)
- Properly raise 400 error on transfer API in case of bad subject or recipient
  [#784](https://github.com/opendatateam/udata/pull/784)
- Fix broken OEmbed rendering [#783](https://github.com/opendatateam/udata/issues/783)
- Improve crawlers behavior by adding some `meta[name=robots]` on pages requiring it
  [#777](https://github.com/opendatateam/udata/pull/777)

## 1.0.1 (2017-02-16)

- Pin PyMongo version (only compatible with PyMongo 3+)

## 1.0.0 (2017-02-16)

### Breaking Changes

* 2016-05-11: Upgrade of ElasticSearch from 1.7 to 2.3 [#449](https://github.com/opendatateam/udata/pull/449)

You have to re-initialize the index from scratch, not just use the `reindex` command given that ElasticSearch 2+ doesn't provide a way to [delete mappings](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-delete-mapping.html) anymore. The command is `udata search init` and may take some time given the amount of data you are dealing with.

* 2017-01-18: User search and listing has been removed (privacy concern)

### New & Improved

* 2017-01-06: Add some dataset ponderation factor: temporal coverage, spatial coverage,
  certified provenance and more weight for featured ones. Need reindexation to be taken into account.

* 2016-12-20: Use all the [Dublin Core Frequencies](http://dublincore.org/groups/collections/frequency/)
  plus some extra frequencies.

* 2016-12-01: Add the possibility for a user to delete its account in the admin interface

In some configurations, this feature should be deactivated, typically when
there is an SSO in front of udata which may cause some inconsistencies. In
that case, the configuration parameter DELETE_ME should be set to False (True
by default).

* 2016-05-12: Add fields masks to reduce API payloads [#451](https://github.com/opendatateam/udata/pull/451)

The addition of [fields masks](http://flask-restplus.readthedocs.io/en/stable/mask.html) in Flask-RESTPlus allows us to reduce the retrieved payload within the admin — especially for datasets — and results in a performances boost.

### Fixes

* 2016-11-29: Mark active users as confirmed [#619](https://github.com/opendatateam/udata/pull/618)
* 2016-11-28: Merge duplicate users [#617](https://github.com/opendatateam/udata/pull/617)
  (A reindexation is necessary after this migration)

### Deprecation

Theses are deprecated and support will be removed in some feature release.
See [Deprecation Policy](https://udata.readthedocs.io/en/stable/versionning/#deprecation-policy).

* Theses frequencies are deprecated for their Dublin Core counter part:
    * `fortnighly` ⇨ `biweekly`
    * `biannual` ⇨ `semiannual`
    * `realtime` ⇨ `continuous`


## 0.9.0 (2017-01-10)

- First published version
