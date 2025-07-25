# Changelog

## Current (in progress)

- Nothing yet

## 10.8.1 (2025-07-25)

- Fix user deletion performances issues [#3388](https://github.com/opendatateam/udata/pull/3388)
- Add search to discussions [#3384](https://github.com/opendatateam/udata/pull/3384)
- Separate metrics for opened discussions [#3370](https://github.com/opendatateam/udata/pull/3370)

## 10.8.0 (2025-07-22)

- Remove placeholder Jinja filter [#3372](https://github.com/opendatateam/udata/pull/3372/)
- Add `self_web_url` for discussion [#3375](https://github.com/opendatateam/udata/pull/3375)
- Fix dataset schemas endpoint when no resource [#3373](https://github.com/opendatateam/udata/pull/3373)
- Add last_update as a dataset model property [#3377](https://github.com/opendatateam/udata/pull/3377)
- Add `label` (translation of role) to API response for org members [#3383](https://github.com/opendatateam/udata/pull/3383)
- Fix crashing on datasets with no slugs [#3368](https://github.com/opendatateam/udata/pull/3368/)
- Fix duplicate contact point creation [#3379](https://github.com/opendatateam/udata/pull/3379) [#3381](https://github.com/opendatateam/udata/pull/3381)
- Atomic `get_or_create` [#3366](https://github.com/opendatateam/udata/pull/3366)
- Add contact points suggest [#3376](https://github.com/opendatateam/udata/pull/3376)

## 10.7.0 (2025-07-17)

- Add name and siret filters for orgs [#3362](https://github.com/opendatateam/udata/pull/3362)
- Refactor how to get URLs to the cdata front-end, need to set the `CDATA_BASE_URL` env variable (removal of `endpoint_for()`, `fields.UrlFor()`, `display_url`, `external_url` and `external_url_with_campaign`) [#3345](https://github.com/opendatateam/udata/pull/3345) [#3371](https://github.com/opendatateam/udata/pull/3371)
- Add back preview_url from tabular API (remove the PreviewPlugin system) [#3364](https://github.com/opendatateam/udata/pull/3364)
- Do not crash on invalid schemas API JSON [#3363](https://github.com/opendatateam/udata/pull/3363/)
- Fix flaky test on timed recent Atom feeds [#3365](https://github.com/opendatateam/udata/pull/3365)
- Allow to remove checksum from resource [#3369](https://github.com/opendatateam/udata/pull/3369)

## 10.6.0 (2025-07-08)

- Add config entry for ISO-DCAT XSLT URL [#3360](https://github.com/opendatateam/udata/pull/3360)
- Fix failing to return dataservice in harvest preview because of no ID for URL [#3357](https://github.com/opendatateam/udata/pull/3357/)
- Fix invalid resource format from harvested RDF records [#3354](https://github.com/opendatateam/udata/pull/3354)
- Expose `dataset_id` for CommunityResource in /dataset/resource/id [#3258](https://github.com/opendatateam/udata/pull/3258)
- Add a CI job to create a release on Sentry [#3266](https://github.com/opendatateam/udata/pull/3266)
- Sort extensions in `/api/1/datasets/extensions/` response alphabetically [#3358](https://github.com/opendatateam/udata/pull/3358)
- Migrate recommendations tasks, [udata-recommendations](https://github.com/opendatateam/udata-recommendations/) is no longer required [#3355](https://github.com/opendatateam/udata/pull/3355)
- Migrate udata-transport tasks, [udata-transport](https://github.com/opendatateam/udata-transport/) is no longer required [#3355](https://github.com/opendatateam/udata/pull/3355)

## 10.5.0 (2025-07-02)

- Allow temporal intervals with no start date [#3353](https://github.com/opendatateam/udata/pull/3353)
- Fix removing schema by sending null [#3350](https://github.com/opendatateam/udata/pull/3350)
- Use datagouv patched ISO-DCAT XSLT URL [#3351](https://github.com/opendatateam/udata/pull/3351)

## 10.4.3 (2025-06-23)

- Add access audience to dataservices [#3334](https://github.com/opendatateam/udata/pull/3334)
- Lock the updates of the resources list [#3338](https://github.com/opendatateam/udata/pull/3338)
- Expose permissions to cdata [#3336](https://github.com/opendatateam/udata/pull/3336)
- Add endpoint to get datasets followed by user [#3337](https://github.com/opendatateam/udata/pull/3337)
- Do not harvest spatial with invalid values [#3341](https://github.com/opendatateam/udata/pull/3341)
- Allow global admins to manually run harvesters in production [#3340](https://github.com/opendatateam/udata/pull/3340)
- Add monthly metrics to datasets, dataservices, reuses and organizations [#3342](https://github.com/opendatateam/udata/pull/3342)
- Fix user avatar deletion [#3346](https://github.com/opendatateam/udata/pull/3346)

## 10.4.2 (2025-06-05)

- :warning: Add migration to clean duplicate activities [#3327](https://github.com/opendatateam/udata/pull/3327)
- Add test for removing last contact point [#3322](https://github.com/opendatateam/udata/pull/3322)
- Add activities to dataservices, topics and resources, add Auditable class to refactor improve code [#3308](https://github.com/opendatateam/udata/pull/3308) [#3333](https://github.com/opendatateam/udata/pull/3333)
- Store activities for private objects [#3328](https://github.com/opendatateam/udata/pull/3328)
- Do not crash if file doesn't exists during resource deletion [#3323](https://github.com/opendatateam/udata/pull/3323)
- Show user domain in suggest [#3324](https://github.com/opendatateam/udata/pull/3324)
- Add new global site metrics [#3325](https://github.com/opendatateam/udata/pull/3325)
- Keep the existing frequency if not found during harvesting [#3330](https://github.com/opendatateam/udata/pull/3330)
- Migrate atom feeds from udata-front to udata [#3326](https://github.com/opendatateam/udata/pull/3326)
- Add organization dataservices catalog route [#3332](https://github.com/opendatateam/udata/pull/3332)

## 10.4.1 (2025-05-20)

- Remove duplicate `downloads` in dataset csv adapter [#3319](https://github.com/opendatateam/udata/pull/3319)
- Add missing default for license full object [#3317](https://github.com/opendatateam/udata/pull/3317/)
- Check for slugs in followers API [#3320](https://github.com/opendatateam/udata/pull/3320)
- Fix missing ID in dataset reuses mask [#3321](https://github.com/opendatateam/udata/pull/3321)

## 10.4.0 (2025-05-15)

- Improve reuse api perfs by adding a mask on datasets [#3309](https://github.com/opendatateam/udata/pull/3309)
- Private objects should return 404 by api [#3311](https://github.com/opendatateam/udata/pull/3311) [#3316](https://github.com/opendatateam/udata/pull/3316)
- Allow returning full sub-objects (license, frequency, zones and granularity) for datasets APIv2 [#3310](https://github.com/opendatateam/udata/pull/3310)
- Add `featured` to dataset default mask [#3313](https://github.com/opendatateam/udata/pull/3313)
- Add endpoint to get all schemas for a dataset without fetching resources [#3314](https://github.com/opendatateam/udata/pull/3314)

## 10.3.2 (2025-05-06)

- feat(topics): add featured filter in API [#3301](https://github.com/opendatateam/udata/pull/3301)
- Improve wording on account inactivity emails [#3304](https://github.com/opendatateam/udata/pull/3304)
- Migrate CSV exports from udata-front to udata (requires adding redirection to Nginx) [#3306](https://github.com/opendatateam/udata/pull/3306)
- Add reuse filter on datasets API [#3307](https://github.com/opendatateam/udata/pull/3307)

## 10.3.1 (2025-04-29)

- Add archived, deleted and private filter in dataset list api [#3298](https://github.com/opendatateam/udata/pull/3298)
- Exclude deleted dataservices in csv queryset [#3297](https://github.com/opendatateam/udata/pull/3297)
- Publish comments on behalf of org, close without message and edit/delete discussions comments [#3295](https://github.com/opendatateam/udata/pull/3295)
- Migrate MAAF backend from udata-front [#3300](https://github.com/opendatateam/udata/pull/3300)
- Follow: add user parser argument [#3302](https://github.com/opendatateam/udata/pull/3302)
- Allow trailing slash to activity route [#3303](https://github.com/opendatateam/udata/pull/3303)

## 10.3.0 (2025-04-11)

- Skip empty datasets nodes referenced in dataservices before creating an harvest job item [#3285](https://github.com/opendatateam/udata/pull/3285)
- Harvest Distribution with a DCAT.accessService property as type `api` [#3294](https://github.com/opendatateam/udata/pull/3294)
- Add search to harvest sources [#3296](https://github.com/opendatateam/udata/pull/3296)
- Refactor error management [#3292](https://github.com/opendatateam/udata/pull/3292)
- Compute quality score to show correct resources score in api v2 [#3290](https://github.com/opendatateam/udata/pull/3290/)

## 10.2.0 (2025-04-02)

- Fix wrong error message when updating the GeoZone of a dataset with already a Geometry [#3271](https://github.com/opendatateam/udata/pull/3271)
- Update dependencies [#3278](https://github.com/opendatateam/udata/pull/3278)
  - Some of these upgrades implied code changes in udata, udata-front or udata-ckan:
    - upgrade bleach to 6.2.0
    - upgrade html2text to 2024.2.26
    - upgrade mistune to 3.1.3
    - upgrade netaddr to 1.3.0
    - upgrade wtforms to 3.2.1
    - upgrade voluptuous to 0.15.2
    - replace StringDist by Levenshtein
  - Did not upgrade Flask (and its plugins), blinker and werkzeug yet

## 10.1.4 (2025-03-24)

- Improve datasets' API perfs (do not fetch resources from Mongo, add /api/2/datasets endpoint…) [#3279](https://github.com/opendatateam/udata/pull/3279) [#3291](https://github.com/opendatateam/udata/pull/3291)
- Fix harvesting literal contact points [#3288](https://github.com/opendatateam/udata/pull/3288)
- Use YEARS_OF_INACTIVITY_BEFORE_DELETION all around in code [#3287](https://github.com/opendatateam/udata/pull/3287)
- Add a udata catalog in dcat backends to test [#3289](https://github.com/opendatateam/udata/pull/3289)
- Add safeguards in the resource reorder endpoint [#3243](https://github.com/opendatateam/udata/pull/3243)

## 10.1.3 (2025-03-14)

- Add inactive users notification and deletion jobs [#3274](https://github.com/opendatateam/udata/pull/3274)
  - these jobs can be scheduled daily for example
  - `YEARS_OF_INACTIVITY_BEFORE_DELETION` setting must be configured at least to activate it
- **breaking change** Migrate dataservices fields, migration needed [#3262](https://github.com/opendatateam/udata/pull/3262)
- Add views as Dataservice metrics and sort [#3280](https://github.com/opendatateam/udata/pull/3280)
- Fix creating/updating ID for resources [#3239](https://github.com/opendatateam/udata/pull/3239)
- Cannot respond to a transfer after first response [#3255](https://github.com/opendatateam/udata/pull/3255)
- Cannot update resource filetype after creation [#3254](https://github.com/opendatateam/udata/pull/3254)
- Add `last_login_at` in user endpoints for super-admins [#3284](https://github.com/opendatateam/udata/pull/3284)
- Add autoarchive to dataservices [#3283](https://github.com/opendatateam/udata/pull/3283)

## 10.1.2 (2025-03-10)

- Fix end date not defined in admin [#3281](https://github.com/opendatateam/udata/pull/3281)

## 10.1.1 (2025-03-03)

- Allow temporal coverage with only a start date [#3192](https://github.com/opendatateam/udata/pull/3192)
- The `extras` column in the resource catalog is now dumped as json [#3272](https://github.com/opendatateam/udata/pull/3272) and [#3273](https://github.com/opendatateam/udata/pull/3273)
- Ensure we populate slug properly on user deletion [#3277](https://github.com/opendatateam/udata/pull/3277)

## 10.1.0 (2025-02-20)

- **breaking change** Harvest attribution roles [#3149](https://github.com/opendatateam/udata/pull/3149) [#3270](https://github.com/opendatateam/udata/pull/3270)
  - dataset and dataservices now have a list of contact points
  - migration needed
- Allow super-admins to change objects' owners [#3260](https://github.com/opendatateam/udata/pull/3260)
- Fix contact point permissions [#3253](https://github.com/opendatateam/udata/pull/3253)
- Fix wrong marshal for community resource uploads [#3261](https://github.com/opendatateam/udata/pull/3261)
- Return harvesters's errors details only for super-admins [#3264](https://github.com/opendatateam/udata/pull/3264)
- feat: topics list filtered by visible_by_user [#3265](https://github.com/opendatateam/udata/pull/3265)
- Allow geozone suggest to check the id field [#3267](https://github.com/opendatateam/udata/pull/3267)
- Allow a user to check its own membership requests [#3269](https://github.com/opendatateam/udata/pull/3269)

## 10.0.8 (2025-01-31)

- Force the usage of transfers request to change the owner of a model [#3249](https://github.com/opendatateam/udata/pull/3249)
- Add report of duplicates resources ids [#3247](https://github.com/opendatateam/udata/pull/3247)
- Add search to posts [#3248](https://github.com/opendatateam/udata/pull/3248)
- Resource catalog: fix preview_url and add extras [#3188](https://github.com/opendatateam/udata/pull/3188)
- Add trailing slash to security routes [#3251](https://github.com/opendatateam/udata/pull/3251)
- Upgrade packaging dependency to 24.2 [#3252](https://github.com/opendatateam/udata/pull/3252)
- Expose HVD dataservice as inline distribution [#3256](https://github.com/opendatateam/udata/pull/3256)

## 10.0.7 (2025-01-13)

- Add a test to clear datasets on Topics api v1 [#3233](https://github.com/opendatateam/udata/pull/3233)
- feat: optimize topic's datasets reindex [#3234](https://github.com/opendatateam/udata/pull/3234)
- Allow Dataservice transfer [#3237](https://github.com/opendatateam/udata/pull/3237)
- fix `function_field` wrong name [#3236](https://github.com/opendatateam/udata/pull/3236)
- Allow dataservice archive [#3238](https://github.com/opendatateam/udata/pull/3238)
- Improve OGC service detection to expose in RDF [#3241](https://github.com/opendatateam/udata/pull/3241)
- Don’t duplicate datasets with a harvest.remote_id URI when harvesting [#3219](https://github.com/opendatateam/udata/pull/3219)
- Fix version number build in CI [#3244](https://github.com/opendatateam/udata/pull/3244)

## 10.0.6 (2024-12-19)

- Ignore inactive sources at harvest time [#3226](https://github.com/opendatateam/udata/pull/3226)
    - If some harvest sources were marked inactive by mistake, they won't get executed anymore
- Organization url is now a URLField and should be a valid URL [#3227](https://github.com/opendatateam/udata/pull/3227)
- Fix the `parse-url` command [#3225](https://github.com/opendatateam/udata/pull/3225)
- Add `with_drafts` argument to posts API [#3229](https://github.com/opendatateam/udata/pull/3229)
- Fix failing dataset save in update reuses metrics [#3230](https://github.com/opendatateam/udata/pull/3230)
- Fix catalog RDF by preventing memory increase on getting dataservice hvd tags [#3231](https://github.com/opendatateam/udata/pull/3231)
- Update purge tasks [#3167](https://github.com/opendatateam/udata/pull/3167)
- Trigger GitLab infra deployment through simple-scaffolding script [#3232](https://github.com/opendatateam/udata/pull/3232)

## 10.0.5 (2024-12-09)

- Add list transfers endpoint / Save user requesting the transfer [#3211](https://github.com/opendatateam/udata/pull/3211)
- Add dataservice csv adapter [#3208](https://github.com/opendatateam/udata/pull/3208)
- Add url_for for dataservices and mail notifications [#3213](https://github.com/opendatateam/udata/pull/3213)
- Compute dataservices metrics on org, user and site [#3209](https://github.com/opendatateam/udata/pull/3209)
- Update default method blocklist for READ ONLY mode [#3212](https://github.com/opendatateam/udata/pull/3212)
- The API will now return all the datasets a user has access to, including deleted of private ones that they're the owners of [#3214](https://github.com/opendatateam/udata/pull/3214)
- Rename administration labels from "Private" to "Draft" [#3217](https://github.com/opendatateam/udata/pull/3217)
- Add partial obfuscation of email for members [#3220](https://github.com/opendatateam/udata/pull/3220)
- Reuse url is now a URLField and should be a valid URL [#3222](https://github.com/opendatateam/udata/pull/3222)

## 10.0.4 (2024-11-29)

- Add created and last_modified sorts on dataservice list [#3206](https://github.com/opendatateam/udata/pull/3206)
- Fix dataservice metadata_modified_at update in API [#3207](https://github.com/opendatateam/udata/pull/3207)
- Escape modal title in admin [#3210](https://github.com/opendatateam/udata/pull/3210)
- feat: handle multiple tags on datasets and topics apis [#3204](https://github.com/opendatateam/udata/pull/3204)

## 10.0.3 (2024-11-27)

- Expose OGC services distributions as dataservice [#3203](https://github.com/opendatateam/udata/pull/3203)
- Add a matomo "campaign" parameter on links in emails if `MAIL_CAMPAIGN` is configured [#3190](https://github.com/opendatateam/udata/pull/3190)
- Use a safe XML parser that doesn't resolve entities, update lxml to 5.3.0 [#3205](https://github.com/opendatateam/udata/pull/3205)
- Add DCAT-AP HVD properties in RDF output if the dataservice or its datasets are tagged hvd [#3187](https://github.com/opendatateam/udata/pull/3187)
- Only keep the "local authority" org badge if it's also a "public service" [#3200](https://github.com/opendatateam/udata/pull/3200)

## 10.0.2 (2024-11-19)

- Use correct DCAT.service predicate in RDF output [#3199](https://github.com/opendatateam/udata/pull/3199)
- Fix the Badge.badge_label method [#3198](https://github.com/opendatateam/udata/pull/3198)
- Skip servesDataset for tabular API dataservice (temporary fix) [#3196](https://github.com/opendatateam/udata/pull/3196)

## 10.0.1 (2024-11-15)

- Add more comments and types in the `api_field.py` "lib" [#3174](https://github.com/opendatateam/udata/pull/3174)
- Allow overriding of badges (for example in plugins like udata-front) [#3191](https://github.com/opendatateam/udata/pull/3191)
- Add link to new admin in existing udata admin based on `NEW_ADMIN_URL` setting [#3194](https://github.com/opendatateam/udata/pull/3194)
- Add business documentation url property on dataservice [#3193](https://github.com/opendatateam/udata/pull/3193)
- Expose the dataset's alternate identifier in RDF [#3186](https://github.com/opendatateam/udata/pull/3186)

## 10.0.0 (2024-11-07)

- **breaking change** Migrate organization badges label to lowercase [#3182](https://github.com/opendatateam/udata/pull/3182)
- Add contact_form in ContactPoint api fields [#3175](https://github.com/opendatateam/udata/pull/3175)
- Expose contact point in DCAT RDF [#3179](https://github.com/opendatateam/udata/pull/3179)
- Use trailing slashes for the upload files URLs [#3177](https://github.com/opendatateam/udata/pull/3177)
- Use hydra's RESTful endpoint URLs [#3146](https://github.com/opendatateam/udata/pull/3146)
- Return dataservices visible to the user [#3180](https://github.com/opendatateam/udata/pull/3180)
- Fix flaky "duplicated email" importing fixtures tests [#3176](https://github.com/opendatateam/udata/pull/3176)
- Fix deprecated CircleCI config [#3181](https://github.com/opendatateam/udata/pull/3181)
- Use proper RESTful Hydra API endpoints [#3178](https://github.com/opendatateam/udata/pull/3178)
- Add a "filter by organization badge" for datasets, dataservices, reuses and organizations [#3155](https://github.com/opendatateam/udata/pull/3155)
    * you will need https://github.com/opendatateam/udata-search-service/pull/49 for the search service
- Add dataservices search with search-service [#3171](https://github.com/opendatateam/udata/pull/3171)
    * you will need https://github.com/opendatateam/udata-search-service/pull/48
- Expose the "landingPage" in DCAT RDF [#3183](https://github.com/opendatateam/udata/pull/3183)
- Licence.guess: extract first URL for better matching [#3185](https://github.com/opendatateam/udata/pull/3185)

## 9.2.4 (2024-10-22)

- Add a job to bind Tabular API to its datasets [#3162](https://github.com/opendatateam/udata/pull/3162)
- Expose dataservices' datasets by link instead of list [#3156](https://github.com/opendatateam/udata/pull/3156)
- CSW ISO Harvest: add extra_configs.remote_url_prefix [#3157](https://github.com/opendatateam/udata/pull/3157)
- DCAT harvest : Refactor DCAT extras handling in rdf parsing [#3054](https://github.com/opendatateam/udata/pull/3054). `accesRights`, `rights` and `license` are now in `extras["dcat"]` for both datasets and resources. `accessRights` can be infered for a dataset from its resources.

## 9.2.3 (2024-10-14)

- Add migration to delete duplicate resources due to ODS harvesting [#3158](https://github.com/opendatateam/udata/pull/3158)
- Add discussion.posted_on in discussion sort choices [3168](https://github.com/opendatateam/udata/pull/3168)

## 9.2.2 (2024-10-08)

- Add a filter on organization and document sort parameters in the `/discussions` endpoint [#3147](https://github.com/opendatateam/udata/pull/3147)
- Move discussion catalog creation and add fields [#3152](https://github.com/opendatateam/udata/pull/3152) and [#3154](https://github.com/opendatateam/udata/pull/3154)
- Add resources formats and harvest remote_url on dataset catalog [#3159](https://github.com/opendatateam/udata/pull/3159)
- Add contact form in contact point model [#3164](https://github.com/opendatateam/udata/pull/3164)
- Make base_api_url optional in dataservice [https://github.com/opendatateam/udata/pull/3163](#3163)

## 9.2.1 (2024-09-23)

- Enable basic search on dataservices [#3148](https://github.com/opendatateam/udata/pull/3148)

## 9.2.0 (2024-09-13)

- Allow OAuth clients without secrets [#3138](https://github.com/opendatateam/udata/pull/3138)
- Add a `archived` button for datasets and reuses on frontend admin [#3104](https://github.com/opendatateam/udata/pull/3104)
- **breaking change** Return all the reuses available to a user on the /reuses endpoint, including the private and deleted ones they own [#3140](https://github.com/opendatateam/udata/pull/3140).
- Fix undelete reuse and dataservices [#3141](https://github.com/opendatateam/udata/pull/3141)
- Add a minimal publiccode.yml [#3144](https://github.com/opendatateam/udata/pull/3144)
- Fix the boolean filters in the API for the "new system" endpoints [#3139](https://github.com/opendatateam/udata/pull/3139)
- Update authlib dependency from 0.14.3 to 1.3.1 [#3135](https://github.com/opendatateam/udata/pull/3135)
- Add CORS on resource redirect [#3145](https://github.com/opendatateam/udata/pull/3145)

## 9.1.4 (2024-08-26)

- Fix many linting issues reported by ruff [#3118](https://github.com/opendatateam/udata/pull/3118)
- Import the dataservice's organization from the fixtures [#3121](https://github.com/opendatateam/udata/pull/3121)
- Convert reuse to new API system [#3066](https://github.com/opendatateam/udata/pull/3066)
- Fix circular import error [#3128](https://github.com/opendatateam/udata/pull/3128)
- Add an option to specify the port when using `inv serve` [#3123](https://github.com/opendatateam/udata/pull/3123)
- Add a new `related_to` filter parameter to the activities API endpoint [#3127](https://github.com/opendatateam/udata/pull/3127)
- Properly import the `Discussion.closed_by` from the fixtures [#3125](https://github.com/opendatateam/udata/pull/3125)
- Send an API token to Hydra when publishing resource events [#3130](https://github.com/opendatateam/udata/pull/3130)
- Add `last_login_at` to org members API [#3133](https://github.com/opendatateam/udata/pull/3133)
- Always add Vary even for non CORS requests [#3132](https://github.com/opendatateam/udata/pull/3132)
- Add acronym in organization csv catalog [#3134](https://github.com/opendatateam/udata/pull/3134)
- Limit the number of user suggestions [#3131](https://github.com/opendatateam/udata/pull/3131)

## 9.1.3 (2024-08-01)

- Adds latest `sentry-sdk[flask]` as an install dependency, and update Sentry logic to be able to send environment, app version and profiling/performance info [#3086](https://github.com/opendatateam/udata/pull/3086)
- Add report get endpoint and make report get and list admin only [#3115](https://github.com/opendatateam/udata/pull/3115)
- Fix the version of udata-fixtures used by `udata import-fixtures` [#3114](https://github.com/opendatateam/udata/pull/3114)
- Update to the version v2.0.0 of udata-fixtures (with the dataservices)
- Add type hints [#3111](https://github.com/opendatateam/udata/pull/3111)
- Make sure requests v2.32.3 is used everywhere consistently [#3116](https://github.com/opendatateam/udata/pull/3116)
- Expose a dataservice in its organization's catalog, and expose a dataservice's catalog [#3122](https://github.com/opendatateam/udata/pull/3122)

## 9.1.2 (2024-07-29)

- Add a `archived` field for reuses [#3088](https://github.com/opendatateam/udata/pull/3088)
- Add linter and formatter with `pyproject.toml` config, add lint and formatting step in CI, add pre-commit hook to lint and format, update docs and lint and format the code [#3085](https://github.com/opendatateam/udata/pull/3085)
- Revamp CORS: remove flask-cors to always returns 204 on OPTIONS request [#3074](https://github.com/opendatateam/udata/pull/3074)
- Update pinned dependencies according to project dependencies, without updating any project dependencies [#3089](https://github.com/opendatateam/udata/pull/3089)
- Add "run" button to harvesters (configurable with `HARVEST_ENABLE_MANUAL_RUN`) [#3092](https://github.com/opendatateam/udata/pull/3092)
- Move from `object_type` / `object_id` to `subject_type` / `subject_id` in reports API [#3094](https://github.com/opendatateam/udata/pull/3094)
- Allow to report without being authenticated [#3096](https://github.com/opendatateam/udata/pull/3096)
- Add a warning on harvest source deletion [#3098](https://github.com/opendatateam/udata/pull/3098)
- Fix license in dataservices API (now returns ID instead of title) [#3097](https://github.com/opendatateam/udata/pull/3097)
- Fix missing title on new dataset preview [#3100](https://github.com/opendatateam/udata/pull/3100)
- Fix the fixtures tests which was not running, and then was failing [#3105](https://github.com/opendatateam/udata/pull/3105)
- Refactoring of the fixtures, the `generate-fixtures` command has been renamed to `import-fixtures` [#3106](https://github.com/opendatateam/udata/pull/3106)

## 9.1.1 (2024-07-16)

- Add correct owner permissions on harvest sources [#3091](https://github.com/opendatateam/udata/pull/3091)

## 9.1.0 (2024-07-11)

- Add reports backend [#3069](https://github.com/opendatateam/udata/pull/3069) and [#3078](https://github.com/opendatateam/udata/pull/3078)
- Improve `udata db check-integrity` (perfs, Sentry notifications…) [#3026](https://github.com/opendatateam/udata/pull/3026)
- Harvest dataservices [#3029](https://github.com/opendatateam/udata/pull/3029)
- Refactor catalog exports [#3052](https://github.com/opendatateam/udata/pull/3052)
- Add a filter to filter dataservices by dataset [#3056](https://github.com/opendatateam/udata/pull/3056)
- Fix reuses' datasets references [#3057](https://github.com/opendatateam/udata/pull/3057)
- Save and show harvest logs [#3053](https://github.com/opendatateam/udata/pull/3053)
- Fix missing `ObjectId` validation on `/sources` endpoint [#3060](https://github.com/opendatateam/udata/pull/3060)
- Improve URL validation errors [#3063](https://github.com/opendatateam/udata/pull/3063) [#2768](https://github.com/opendatateam/udata/pull/2768)
- Do not return full dataset objects on dataservices endpoints [#3068](https://github.com/opendatateam/udata/pull/3068)
- Update markdown base settings [#3067](https://github.com/opendatateam/udata/pull/3067)
- Prevent tagging as spam owners' messages [#3071](https://github.com/opendatateam/udata/pull/3071)[#3076](https://github.com/opendatateam/udata/pull/3076)
- Add api endpoint /me/org_topics/ [#3070](https://github.com/opendatateam/udata/pull/3070)
- Expose dataservices in RDF catalog [#3058](https://github.com/opendatateam/udata/pull/3058) [#3075](https://github.com/opendatateam/udata/pull/3075)
- CORS: always returns 204 on OPTIONS request [#3046](https://github.com/opendatateam/udata/pull/3046)

## 9.0.0 (2024-06-07)

- **breaking change** Harvest backend is now sync [#3030](https://github.com/opendatateam/udata/pull/3030)
- Add DCAT-AP HVD properties in RDF output if the dataset is tagged hvd [#3050](https://github.com/opendatateam/udata/pull/3050)
- Allow dataservices to be discussed and followed [#3049](https://github.com/opendatateam/udata/pull/3049)
- Add purge-dataservices job [#3049](https://github.com/opendatateam/udata/pull/3049)
- Harvest all the available polygons from a spatial coverage [#3039](https://github.com/opendatateam/udata/pull/3039)

## 8.0.1 (2024-05-28)

- Add dataservices in beta [#2986](https://github.com/opendatateam/udata/pull/2986)
- Remove deprecated `metrics_for` route [#3022](https://github.com/opendatateam/udata/pull/3022)
- Fix spatial coverage fetching perfs. Need to schedule `compute-geozones-metrics` [#3018](https://github.com/opendatateam/udata/pull/3018)
- Delete a user without sending mail [#3031](https://github.com/opendatateam/udata/pull/3031)
- Convert known HVD categories used as theme to keywords [#3014](https://github.com/opendatateam/udata/pull/3014)
- Allow for series in CSW ISO 19139 DCAT backend [#3028](https://github.com/opendatateam/udata/pull/3028)
- Add `email` to membership request list API response, add `since` to org members API responses, add `email` to members of org on show org endpoint for org's admins and editors [#3038](https://github.com/opendatateam/udata/pull/3038)
- Add `resources_downloads` to datasets metrics [#3042](https://github.com/opendatateam/udata/pull/3042)
- Fix do not override resources extras on admin during update [#3043](https://github.com/opendatateam/udata/pull/3043)
- Endpoint /users is now protected by admin permissions [#3047](https://github.com/opendatateam/udata/pull/3047)
- Fix trailing `/` inside `GeoZone` routes not redirecting. Disallow `/` inside `GeoZone` ids [#3045](https://github.com/opendatateam/udata/pull/3045)

## 8.0.0 (2024-04-23)

- **breaking change** Migrate to Python 3.11 [#2992](https://github.com/opendatateam/udata/pull/2992) [#3021](https://github.com/opendatateam/udata/pull/3021)
- **breaking change** Fix datetime serialization in extras (return ISO string in JSON). Warning, `ujson` shouldn't be installed anymore on the project to allow `cls` parameter to override the JSONEncoder [#3019](https://github.com/opendatateam/udata/pull/3019)
- Fix missing `bcrypt` dependency [#3019](https://github.com/opendatateam/udata/pull/3019)

## 7.0.7 (2024-04-16)

- :warning: **breaking change** `DATASET_MAX_RESOURCES_UNCOLLAPSED` config is removed.
- Replace schemas API with a simple proxy to the `schemas.json` file [#2989](https://github.com/opendatateam/udata/pull/2989)
- Topic: add filters in API [#3007](https://github.com/opendatateam/udata/pull/3007)
- Move constants outside `models.py` files to `constants.py` [#3001](https://github.com/opendatateam/udata/pull/3001)
- Move `db` and Mongo fields classes outside `udata.models` [#3005](https://github.com/opendatateam/udata/pull/3005)
- :warning: Update LICENSE_GROUPS config layout [#3010](https://github.com/opendatateam/udata/pull/3010)
- Remove unused dependencies [#3006](https://github.com/opendatateam/udata/pull/3006)
- Move `FieldValidationError` into its own module and add an error handler [#3012](https://github.com/opendatateam/udata/pull/3012)
- Move some `import User` to runtime imports [#3013](https://github.com/opendatateam/udata/pull/3013)
- Move `Owned` mixin to its own module [#3008](https://github.com/opendatateam/udata/pull/3008)
- Move `badge_fields` to separate module than `models.py` [#3011](https://github.com/opendatateam/udata/pull/3011)

## 7.0.6 (2024-03-29)

- Add new harvester for ISO DCAT with XSLT transform [#2982](https://github.com/opendatateam/udata/pull/2982)
- Fix, do not fail on spatial coverage harvesting exception and allow literal spatial BBOX from Arcgis [2998](https://github.com/opendatateam/udata/pull/2998)
- Mock calls to example.com [#3000](https://github.com/opendatateam/udata/pull/3000)
- Fix duplicate logs in console commands [#2996](https://github.com/opendatateam/udata/pull/2996)
- Refactor `Activity.kwargs` into `Activity.extras` to facilitate its usage [#2999](https://github.com/opendatateam/udata/pull/2999)
- :warning: Datasets without resources are now visible and indexable [#2997](https://github.com/opendatateam/udata/pull/2997)

## 7.0.5 (2024-03-20)

- Add spatial coverage harvesting [#2959](https://github.com/opendatateam/udata/pull/2959) [#2991](https://github.com/opendatateam/udata/pull/2991)
- Fix: updating a dataset without `private` do not reset `private` to `False`, the previous saved value is kept [#2955](https://github.com/opendatateam/udata/pull/2955)
- Fix: return the correct error when no `Content-Type` is sent instead of 500 [#2967](https://github.com/opendatateam/udata/pull/2967)
- Improve documentation for API errors [#2952](https://github.com/opendatateam/udata/pull/2965)
- Allow harvesting of big catalog (bigger than 16MB) [#2980](https://github.com/opendatateam/udata/pull/2980) [2985](https://github.com/opendatateam/udata/pull/2985)
- Add downloads' count to organizations CSV [#2973](https://github.com/opendatateam/udata/pull/2973)
- Add 3 new badges to the organization model : `company`, `association` and `local authority` [#2984](https://github.com/opendatateam/udata/pull/2984)
- Prevent geozones listed ad `deleted` to be loaded [#2983](https://github.com/opendatateam/udata/pull/2983) [#2993](https://github.com/opendatateam/udata/pull/2993)
- Topic: add spatial field [#2988](https://github.com/opendatateam/udata/pull/2988)
- Topic: add last_modified field [#2987](https://github.com/opendatateam/udata/pull/2987)
- Add stacktraces to CSV errors [#2990](https://github.com/opendatateam/udata/pull/2990)
- Fix harvesting of DCT.conformsTo for complex inner information [#2994](https://github.com/opendatateam/udata/pull/2994)

## 7.0.4 (2024-02-27)

- Add rotate password command [#2966](https://github.com/opendatateam/udata/pull/2966)
- Custom extras metadata [#2921](https://github.com/opendatateam/udata/pull/2921):
  - Organization can nom define a custom metadata of a choosen type
  - Dataset belonging to the organization can assign a value to the defined metadata
  - Metadata value must match the choosen type by the organization
- Harvest DCAT conformsTo into schemas for resources and datasets [#2949](https://github.com/opendatateam/udata/pull/2949) [#2970](https://github.com/opendatateam/udata/pull/2970) [#2972](https://github.com/opendatateam/udata/pull/2972) [#2976](https://github.com/opendatateam/udata/pull/2976)
- Better reporting in spam detection (show the writer of the discussion/message) [#2965](https://github.com/opendatateam/udata/pull/2965)
- Fix: spam lang detection not lowering input resulting in false positives [#2965](https://github.com/opendatateam/udata/pull/2965)
- Fix: do not send mail about discussions when there is no owner / no organisation members [#2962](https://github.com/opendatateam/udata/pull/2962)
- Fix: 'backend' is now required in `HarvestSource` [#2962](https://github.com/opendatateam/udata/pull/2962)
- Fix: URL to organizations in mails are now independent from `udata-front` (show the URL of the API if no `udata-front`) [#2962](https://github.com/opendatateam/udata/pull/2962)
- Add harvested dcat properties as extras [#2968](https://github.com/opendatateam/udata/pull/2968):
  - DCT.provenance [0..n]
  - DCT.accessRights [0..1]
- Generate translations file [#2974](https://github.com/opendatateam/udata/pull/2974)
- Fix contact point test with missing translation [#2977](https://github.com/opendatateam/udata/pull/2977)
- Remove documentation about maintenance branches [#2979](https://github.com/opendatateam/udata/pull/2979)

## 7.0.3 (2024-02-15)

- Add spam detection and prevention logic on discussion model [#2954](https://github.com/opendatateam/udata/pull/2954) [#2963](https://github.com/opendatateam/udata/pull/2963)
- Fix reuses inside database without private information (default to public) [#2951](https://github.com/opendatateam/udata/pull/2951)
- Fix: you can now remove schema from a resource in the admin [#2950](https://github.com/opendatateam/udata/pull/2950)
- Fix: refuse an organisation access request when multiple access requests are pending [#2960](https://github.com/opendatateam/udata/pull/2960)
- Add downloads count in datasets' CSV [#2953](https://github.com/opendatateam/udata/pull/2953)
- Allow dicts in datasets' extras [#2958](https://github.com/opendatateam/udata/pull/2958)


## 7.0.2 (2024-01-23)

- Improve search serialization perfs for datasets in big topics [#2937](https://github.com/opendatateam/udata/pull/2937)
- Migrate to Flask-Babel because of Flask-BabelEx deprecation [#2897](https://github.com/opendatateam/udata/pull/2897)
- Contact points feature [#2914](https://github.com/opendatateam/udata/pull/2914) [#2943](https://github.com/opendatateam/udata/pull/2943):
  - Users and Organizations can now define a list of contact points
  - Api endpoint for creating, updating and deleting contact points
  - Datasets can define one contact point, among the list of the organization or the user owning the dataset.
  - Defining a contact point for a dataset is done throught a form field
- Allow wildcards in redirect_uris for Oauth2Client [#2935](https://github.com/opendatateam/udata/pull/2935)
- Allow for being one day late on update fulfilled in time [#2941](https://github.com/opendatateam/udata/pull/2941)
- When a topic is deleted, corresponding discussions are purged [#2944](https://github.com/opendatateam/udata/pull/2944)

## 7.0.1 (2023-12-06)

- Add sorting in geozone suggest API endpoint to return zones based on their admin level [#2936](https://github.com/opendatateam/udata/pull/2936)

## 7.0.0 (2023-12-04)

- Prevent sending post_save signals on extras update [#2919](https://github.com/opendatateam/udata/pull/2919)
- Add topic filter on datasets list [#2915](https://github.com/opendatateam/udata/pull/2915)
- Topics: API v2 endpoints [#2913](https://github.com/opendatateam/udata/pull/2913)
- Allow for discussions on Topics [#2922](https://github.com/opendatateam/udata/pull/2922)
- Raise for status on DCAT harvester calls [#2927](https://github.com/opendatateam/udata/pull/2927)
- Harvest dcterms:hasPart as 'other' resource in DCAT [#2928](https://github.com/opendatateam/udata/pull/2928)
- Make sure harvested resources are marked as remote [#2931](https://github.com/opendatateam/udata/pull/2931)
- Use GET and POST harvest BaseBackend utility to have user-agent [#2930](https://github.com/opendatateam/udata/pull/2930)
- Use LazyReferenceField on Topic datasets and reuses [#2924](https://github.com/opendatateam/udata/pull/2924)
- Use harvested dates and not max with internal [#2932](https://github.com/opendatateam/udata/pull/2932)
- Better rdf frequency resilience [#2933](https://github.com/opendatateam/udata/pull/2933)
- :warning: **breaking change** Geozone refactor [#2878](https://github.com/opendatateam/udata/pull/2878):
  - Complete Geozone model refactor, keeping only fields `slug`, `name`, `code`, `level` and adding `uri`
  - Removed parent and validity concept
  - To deploy:
    - Datasets with geozone will return a 500 due to `mongoengine.errors.FieldDoesNotExist: The fields "{'flag', 'dbpedia', ...}" do not exist on the document "GeoZone"`
    - `udata spatial load -d` to load new geozones into the database
    - `udata spatial migrate` to migrate datasets geozones to new ones
    - Reindex datasets (`udata search index dataset`) if using [udata-search-service](https://github.com/opendatateam/udata-search-service)
  - Removed forgotten fields in search [#2934](https://github.com/opendatateam/udata/pull/2934)

## 6.2.0 (2023-10-26)

### New & Improved

- Topics have been refactored and are no more deprecated:
  - Topics creation, update and deletion are now opened to all users [#2898](https://github.com/opendatateam/udata/pull/2898)
  - Topics are now `db.Owned` and searchable by `id` in dataset search [#2901](https://github.com/opendatateam/udata/pull/2901) [#2917](https://github.com/opendatateam/udata/pull/2917)
  - Remove `deleted` api field that does not exist [#2903](https://github.com/opendatateam/udata/pull/2903)
  - Add `created_at`field to topic's model [#2904](https://github.com/opendatateam/udata/pull/2904)
  - Topics can now be filtered by `tag` field [#2904](https://github.com/opendatateam/udata/pull/2904)
  - Topics can now be queried by test search in `name` field with `q` argument [#2904](https://github.com/opendatateam/udata/pull/2904)
- Add support for a CSW harvester using DCAT format [#2800](https://github.com/opendatateam/udata/pull/2800)
- Add German to udata translations [2899](https://github.com/opendatateam/udata/pull/2899)[2909](https://github.com/opendatateam/udata/pull/2909)
- Add harvesters count to site metrics [#2890](https://github.com/opendatateam/udata/pull/2890)
- Use a single session for reindex [#2891](https://github.com/opendatateam/udata/pull/2891)

- Fix site title and keywords never get updated [#2900](https://github.com/opendatateam/udata/pull/2900)
- Reuse's extras are now exposed by API [#2905](https://github.com/opendatateam/udata/pull/2905)
- Add configuration settings to enhance cookies security [#2910](https://github.com/opendatateam/udata/pull/2910)
- Add items.dataset to HarvestJob indexes [#2907](https://github.com/opendatateam/udata/pull/2907)
- Consider acronym when suggesting organization [#2918](https://github.com/opendatateam/udata/pull/2918)

### Fixes

- Return 400 instead of 500 in case of not ObjectID arg in API [#2889](https://github.com/opendatateam/udata/pull/2889)
- Fix default community resource sort parser [#2908](https://github.com/opendatateam/udata/pull/2908)

### Deprecation

- Python 3.7 is now deprecated and will be removed in upcoming release [#2859](https://github.com/opendatateam/udata/pull/2859)
- GeoZone model will be heavily refactored for a simplified version [#2878](https://github.com/opendatateam/udata/pull/2878)

## 6.1.7 (2023-09-01)

- Fix slug overflow with index suffix when reaching max_length [#2874](https://github.com/opendatateam/udata/pull/2874)
- Add extra field to topic model and add it to the dataset search adapter [#2876](https://github.com/opendatateam/udata/pull/2876)
- Upgrade pyyaml in develop and doc deps [#2880](https://github.com/opendatateam/udata/pull/2880)
- Expose dataset's `*_internal` dates in a nested `internal` nested field in api marshalling [#2862](https://github.com/opendatateam/udata/pull/2862)
- Add `business_number_id` metadata for organizations [#2871](https://github.com/opendatateam/udata/pull/2871) [#2887](https://github.com/opendatateam/udata/pull/2887)
- Return 403 when posting comment on discussion closed [#2881](https://github.com/opendatateam/udata/pull/2881)
- Ensure rdf parsed frequency is lowercase [#2883](https://github.com/opendatateam/udata/pull/2883)
- Add a dict of URIs to replace in a RDF graph at harvest time [#2884](https://github.com/opendatateam/udata/pull/2884)
- Fix duplicate recipients in new comments mail [#2886](https://github.com/opendatateam/udata/pull/2886)
- Add type to resource csv adapter [#2888](https://github.com/opendatateam/udata/pull/2888)

## 6.1.6 (2023-07-19)

- Improve DCAT harvest of mime type [#2857](https://github.com/opendatateam/udata/pull/2857)
- Don't crash on files not found when purging resources [2858](https://github.com/opendatateam/udata/pull/2858)
- Improve DCAT catalog exposed [#2860](https://github.com/opendatateam/udata/pull/2860)
- Use the resource's extra `analysis:last-modified-at` in the `last_modified` property [#2863](https://github.com/opendatateam/udata/pull/2863)
- Add optionnal harvest validation form [#2864](https://github.com/opendatateam/udata/pull/2864)
- Fix dataset list default sorting [#2867](https://github.com/opendatateam/udata/pull/2867)
- Update API doc link [#2866](https://github.com/opendatateam/udata/pull/2866)
- Update admin quality progress bar [#2872](https://github.com/opendatateam/udata/pull/2872)

## 6.1.5 (2023-06-19)

- Specify *public* datasets and reuses in admin count [#2852](https://github.com/opendatateam/udata/pull/2852)
- Fix url params being stripped in markdown for internal URLs [#2855](https://github.com/opendatateam/udata/pull/2855)

## 6.1.4 (2023-05-16)

- Upgrade development dependencies [#2844](https://github.com/opendatateam/udata/pull/2844)
- Compile translations for testing [#2845](https://github.com/opendatateam/udata/pull/2845)
- Add user arg to discussion list API [#2842](https://github.com/opendatateam/udata/pull/2842)
- No more sending email, slug and user name to sentry [#2846](https://github.com/opendatateam/udata/pull/2846)
- Add test for passwordless user [#2848](https://github.com/opendatateam/udata/pull/2848)
- Parse IANA and EUROPA URIs format [#2849](https://github.com/opendatateam/udata/pull/2849)
- Dataset last update sorting:
    - Transmit dataset's `last_update` field to search service [#2847](https://github.com/opendatateam/udata/pull/2847)
    - Check if dataset's and resource's harvesting date `modified_at` are ealier than today's date [#2850](https://github.com/opendatateam/udata/pull/2850)
- Upgrade mongoengine and storage deps [#2839](https://github.com/opendatateam/udata/pull/2839):
    - Upgrade flask-storage 1.0.0 -> 1.3.2
    - Upgrade flask-mongoengine 0.9.5 -> 1.0.0, now returning a ValidationError on get_or_404 on invalid id
    - Upgrade mongoengine 0.26.0 -> 0.27.0
-  Prevent raising unecessary error in index command [#2851](https://github.com/opendatateam/udata/pull/2851)
-  Use `datetime.utcnow` to make sure to handle utc datetimes [#2853](https://github.com/opendatateam/udata/pull/2853)

## 6.1.3 (2023-04-18)

- Fix XSS vulnerability: escape user content in selectize items in admin [#2843](https://github.com/opendatateam/udata/pull/2843)
- Fix schema is undefined when checking for schema.url in admin resource form [#2837](https://github.com/opendatateam/udata/pull/2837)
- Fix to_naive_datetime in harvest preview [#2835](https://github.com/opendatateam/udata/pull/2835)
- :warning: Flask-Security update to enable `GenericResponses` [#2826](https://github.com/opendatateam/udata/pull/2826):
    - Upgrade Flask-Security 4.5.1 -> 5.1.1
    - Upgrade WTForms 2.2.1 -> 3.0.1
    - Upgrade WTForms-json 0.3.3 -> 0.3.5
    - New security email template for existing users
- Fix SelectField validation failure following WTForms upgrade [#2841](https://github.com/opendatateam/udata/pull/2841)
- Add `format_timedelta` to `udata.i18n` [#2836](https://github.com/opendatateam/udata/pull/2836)
- Improve send_mail resilience with refused address among recipients [#2840](https://github.com/opendatateam/udata/pull/2840)

## 6.1.2 (2023-03-28)

- Resources schema can now have an URL field. [#2825](https://github.com/opendatateam/udata/pull/2825)
- Fix URLField validation error message [#2831](https://github.com/opendatateam/udata/pull/2831)
- Dates renaming to provide more relevant computed dates between internal and harvested dates [#2815](https://github.com/opendatateam/udata/pull/2815):
    - Removed `published` attribute from Resource model
    - Renamed `created_at` and `last_modified` of Dataset model to `created_at_internal` and `last_modified_internal`
    - Renamed `created_at` and `modified` of Resource model to `created_at_internal` and `last_modified_internal`
    - Added `created_at` computed property in Dataset and Resource model to provide harvested date if present and internal otherwise
    - Added `last_modified` computed property in Dataset and Resource model to provide max date between internal and harvested date
- Fix for PR [#2815](https://github.com/opendatateam/udata/pull/2815) [#2832](https://github.com/opendatateam/udata/pull/2832)
- Fix following dates refactoring [#2815](https://github.com/opendatateam/udata/pull/2815) [#2832](https://github.com/opendatateam/udata/pull/2832)
- Fix dcat harvesting on dcat:Dataset with blank nodes [#2834](https://github.com/opendatateam/udata/pull/2834)
- Add dataset archived field in resource catalog [#2833](https://github.com/opendatateam/udata/pull/2833)

## 6.1.1 (2023-03-17)

- Fix edge case on aware datetime string [#2827](https://github.com/opendatateam/udata/pull/2827)
- :warning: MongoDB support up to 6.0.4 [#2819](https://github.com/opendatateam/udata/pull/2819):
    - Older versions of MongoDB >=3.6 are still supported
    - Upgrade must be done release by release to set the `FeatureCompatibilityVersion` variable like stated in [this](https://www.mongodb.com/docs/v4.2/release-notes/4.0/#upgrade-procedures) documentation.
    - Upgrade pymongo 3.10.1 -> 4.3.3
    - Upgrade mongoengine 0.20.0 -> 0.26.0
- Add IATA `ssim` among allowed file extensions [#2828](https://github.com/opendatateam/udata/pull/2828)
- Copy user mail card back from udata-front [#2822](https://github.com/opendatateam/udata/pull/2822)
- Upgrade node to a version still available [#2830](https://github.com/opendatateam/udata/pull/2830)

## 6.1.0 (2023-03-07)

- :warning: Upgrading Flask to 2.1.2, leading to an upgrade of click (8.0), Flask-BabelEx (0.9.4), Flask-Caching (2.0.2), flask-storage (1.0.0) instead of flask-fs, Flask-Login (0.6.2), flask-restx (1.0.5), Flask-Security-Too (4.1.5), Jinja2 (3.1.2), pillow (9.2.0), werkzeug (2.2.2) [#2816](https://github.com/opendatateam/udata/pull/2816)
  - Use the full path to the caching backend in `CACHE_TYPE`, ex: `flask_caching.backends.redis`. Named backends are deprecated.
  - Werkzeug redirect now returns the relative url as location in response (https://github.com/pallets/werkzeug/issues/2352).
  - Removed functions have been replaced (`contextfilter` and `contextfunction` from Jinja, root imports and `Href` from Werkzeug, `JSONWebSignatureSerializer` from itsdangerous)
  - Prevent multiple blueprint with same name registration (not supported anymore in Flask).
- Removed all code logic related to the `published` date in resource model, now deprecated. :warning: The attribute itself was left in the model because of the complexity of the migration [#2807](https://github.com/opendatateam/udata/pull/2807)
- Add `xlsx` and `docx` as closed format for quality score [#2814](https://github.com/opendatateam/udata/pull/2814)
- Flush latest rows in csv catalog export before storing file [#2818](https://github.com/opendatateam/udata/pull/2818)
- Exposed dates through API are now timezone aware [#2810](https://github.com/opendatateam/udata/pull/2810)
- Fix frequency reminder [#2821](https://github.com/opendatateam/udata/pull/2821)

## 6.0.2 (2023-02-06)

- Handle None values in dataset and resource extras endpoints [#2805](https://github.com/opendatateam/udata/pull/2805)
- Fix default license being selected in form in optional select group [#2809](https://github.com/opendatateam/udata/pull/2809)
- Fix only SHA1 checksum is accepted when uploading resources [#2808](https://github.com/opendatateam/udata/pull/2808)
- Fix organization metrics count [#2811](https://github.com/opendatateam/udata/pull/2811)
- Fix setuptools version used in CI [#2813](https://github.com/opendatateam/udata/pull/2813)
- Add `udata harvest clean` command [#2812](https://github.com/opendatateam/udata/pull/2812)

## 6.0.1 (2023-01-18)

- Add python version requirement <3.10 [#2798](https://github.com/opendatateam/udata/pull/2798)
- Fix date timezone and format for harvest previz [#2799](https://github.com/opendatateam/udata/pull/2799)
- Add support for DCAT startDate and endDate in temporal coverage [#2801](https://github.com/opendatateam/udata/pull/2801)
- New feature: Users can now change their email by themselves [#2792](https://github.com/opendatateam/udata/pull/2792)

## 6.0.0 (2023-01-09)

- :warning: Kafka removal [#2783](https://github.com/opendatateam/udata/pull/2783)[#2794](https://github.com/opendatateam/udata/pull/2794):
  - Resources events publication now uses webhooks
  - Search indexation (at runtime and with index command) are now made through HTTP requests.
  - If you use [udata-search-service](https://pypi.org/project/udata-search-service/), you need to upgrade to the >=2.0.0 version
- Add dedicated extras endpoints on resources and datasets [#2779](https://github.com/opendatateam/udata/pull/2779)
- Enrich catalog with harvest infos [#2789](https://github.com/opendatateam/udata/pull/2789)
- Add optionnal license select group custom setting for admin [#2786](https://github.com/opendatateam/udata/pull/2786)
- Make index setup optional on init based on config [#2797](https://github.com/opendatateam/udata/pull/2797)

## 5.0.2 (2022-11-29)

- :warning: Upgrade to `Flask-Security-Too` version 4.0.0 [#2772](https://github.com/opendatateam/udata/pull/2772):
  - New User model attribute `fs_uniquifier`, migration needed.
  - The `fs_uniquifier` is used to invalidate existing session in case of password reset.
  - The user's `fs_uniquifier` is used instead of the `id` for auth mecanism including permissions.
  - Exhaustive list of changes [here](https://flask-security-too.readthedocs.io/en/stable/changelog.html#version-4-0-0).
- Fix apiv2 swagger with harvest metadata and add apiv2 swagger tests [#2782](https://github.com/opendatateam/udata/pull/2782)
- Improve frequency criterion in quality score [#2771](https://github.com/opendatateam/udata/pull/2771)
- Add quality score to csv catalogs [#2785](https://github.com/opendatateam/udata/pull/2785)
- Optimize DCAT harvesting on large multiple-paged catalogs, introduce `HARVEST_MAX_ITEMS` development setting [#2781](https://github.com/opendatateam/udata/pull/2781)
- Add condition in security mail utils class to avoid mail sending according to config var [#2788](https://github.com/opendatateam/udata/pull/2788)

## 5.0.1 (2022-11-14)

- Fix resource harvest uri validation error [#2780](https://github.com/opendatateam/udata/pull/2780)

## 5.0.0 (2022-11-14)

- :warning: **Breaking change** Use dedicated dynamic harvest metadata for dataset and resources. A migration copies identifying fields from extras to this dedicated metadata field. Extras won't be used anymore for harvest-related information. udata-ckan, udata-ods and udata-front packages are impacted and should be upgraded accordingly [#2762](https://github.com/opendatateam/udata/pull/2762)

## 4.1.3 (2022-11-02)

- Fix image URLs for suggest endpoints [#2761](https://github.com/opendatateam/udata/pull/2761)
- Switch from `Flask-restplus` to its fork `Flask-rest-x` [2770](https://github.com/opendatateam/udata/pull/2770)
- Clean inactive harvest datasets. :warning: a migration archives datasets linked to inactive harvest sources [#2764](https://github.com/opendatateam/udata/pull/2764) [#2773](https://github.com/opendatateam/udata/pull/2773) [#2777](https://github.com/opendatateam/udata/pull/2777)
- Fix randomly failing suggest tests [#2775](https://github.com/opendatateam/udata/pull/2775)
- Fix alt attribute not shown on image [#2776](https://github.com/opendatateam/udata/pull/2776)

## 4.1.2 (2022-09-01)

- Clean up event code [#2751](https://github.com/opendatateam/udata/pull/2751)
- Replace mongo legacy image in CI [#2754](https://github.com/opendatateam/udata/pull/2754)
- Fixes test `test_suggest_datasets_api` by modifying condition [#2759](https://github.com/opendatateam/udata/pull/2759)
- Fix doc name duplicate on rdf endpoints [#2763](https://github.com/opendatateam/udata/pull/2763)

## 4.1.1 (2022-07-08)

- Quality score computation refactoring and now returning it in list datasets endpoint. Update was made in admin too. [#2746](https://github.com/opendatateam/udata/pull/2746)
- :warning: Manifest logic was removed and udata does now work as standalone [#2747](https://github.com/opendatateam/udata/pull/2747)
- Remove map related stuff [#2749](https://github.com/opendatateam/udata/pull/2749)
- Add library udata_event_service to produce Kafka messages [#2743](https://github.com/opendatateam/udata/pull/2743)

## 4.1.0 (2022-06-09)

- Add html support for posts [#2731](https://github.com/opendatateam/udata/pull/2731)
- Use mongo search if `SEARCH_SERVICE_API_URL` variable is not set [#2728](https://github.com/opendatateam/udata/pull/2728)
- Improve resource extension detection [#2729](https://github.com/opendatateam/udata/pull/2729/files)
- Remove resources in dataset search serialization [#2730](https://github.com/opendatateam/udata/pull/2730)
- Add endpoint to directly get specific resource by rid [#2732](https://github.com/opendatateam/udata/pull/2732).
- Publish kafka message when resource is created, modified or deleted [#2733](https://github.com/opendatateam/udata/pull/2733)
- Clean documentation and code with respect to independent search service [#2738](https://github.com/opendatateam/udata/pull/2738)
- Fix size argument in suggests endpoint and corresponding tests [#2739](https://github.com/opendatateam/udata/pull/2739)
- Add udata instance name prefix and action suffix for kafka topics [#2736](https://github.com/opendatateam/udata/pull/2736)
- Fix tokenisation by building an `AND` query (see comments in code) for mongo text search and pagination [#2740](https://github.com/opendatateam/udata/pull/2740)

## 4.0.2 (2022-05-04)

- Remove unused `_total_pages` search property [#2726](https://github.com/opendatateam/udata/pull/2726)
- Use -followers as default suggest sort on datasets, reuses and orgas [#2727](https://github.com/opendatateam/udata/pull/2727)
- Reintroduce user suggest with mongo contains [#2725](https://github.com/opendatateam/udata/pull/2725)

## 4.0.1 (2022-04-11)

- Removed `post_save` signal within `add_resource` and `update_resource` methods. [#2720](https://github.com/opendatateam/udata/pull/2720)
- Refactor and update documentation with latest udata updates [#2717](https://github.com/opendatateam/udata/pull/2717)
- Add harvest csv adapter for a catalog of harvesters [#2722](https://github.com/opendatateam/udata/pull/2722)

## 4.0.0 (2022-03-30)

### Breaking change

Search refactor [#2680](https://github.com/opendatateam/udata/pull/2680)
- :warning: Search changes [#2692](https://github.com/opendatateam/udata/pull/2692):
  - The search feature is not within udata anymore and queries a distant service.
  - The search feature is now optional and is enabled by setting the `SEARCH_SERVICE_API_URL` setting.
  - When search is not enabled, the search endpoints will return a `501 Not Implemented` error.
  - The ModelAdapter, SearchQuery and SearchResult patterns were kept but heavily refactored.
  - udata uses a Kafka producer to send documents to index to the search service.
  - udata uses HTTP request to query the search service.
- :warning: API changes [#2669](https://github.com/opendatateam/udata/pull/2669):
  - List endpoints for organizations, datasets, reuses and users are now querying MongoDB instead of ElasticSearch.
  - Those endpoints use MongoDB full text search when `q` argument is used. Some unused filters on this route were dropped.
  - A new API parser was implemented to replace the search one.
  - The previous ElasticSearch endpoints were moved to APIv2 with the following url pattern: `/{object}/search` (ex: `/datasets/search`).
- :warning: Suggest changes [#2685](https://github.com/opendatateam/udata/pull/2685) and [#2696](https://github.com/opendatateam/udata/pull/2696):
  - Current suggest implementation moved from an Elasticsearch index to a MongoDB query using the term `contains`.
  - The user suggest was entirely removed, as its existence is now less relevant because of the full text search.

## 3.3.3 (2022-03-29)

- Extend dcat properties support (frequency litteral, creation and modification date, landing page and abstract description) [#2715](https://github.com/opendatateam/udata/pull/2715)


## 3.3.2 (2022-03-01)

- **Deprecation**: Topics are now deprecated and will be removed in upcoming releases.
- Use title to improve License guess [#2697](https://github.com/opendatateam/udata/pull/2697)
- Add a `q` argument to the paginated datasets resources endpoint, to search through resources titles. [#2701](https://github.com/opendatateam/udata/pull/2701)
- Delete discussion with deleted user as only participant [#2702](https://github.com/opendatateam/udata/pull/2702)
- Fix error on post creation when adding related reuse [#2704](https://github.com/opendatateam/udata/pull/2704)
- Redirect in endpoints routing now returns 308 instead of 302 in order to keep the method and body. [#2706](https://github.com/opendatateam/udata/pull/2706)
- Delete badges from datasets fixtures. [2709](https://github.com/opendatateam/udata/pull/2709)

## 3.3.1 (2022-01-11)

- Fix fields empty value in admin form to allow for unsetting fields [#2691](https://github.com/opendatateam/udata/pull/2691)
- :warning: Add a new required topic string field on reuses. The associated migration set default topic to `others` [#2689](https://github.com/opendatateam/udata/pull/2689)

## 3.3.0 (2021-12-10)

- :warning: Removed `Issues` code and logic. The corresponding MongoDB collection should be deleted when upgrading Udata. [#2681](https://github.com/opendatateam/udata/pull/2681)
- Fix transfer ownership from org to user [#2678](https://github.com/opendatateam/udata/pull/2678)
- Fix discussion creation on posts [#2687](https://github.com/opendatateam/udata/pull/2687)

## 3.2.2 (2021-11-23)

- Move template hook logic back to udata [#2671](https://github.com/opendatateam/udata/pull/2671) [#2679](https://github.com/opendatateam/udata/pull/2679)
- Add dataset's acronym to catalog [#2675](https://github.com/opendatateam/udata/pull/2675)
- Better URL-based License guess [#2672](https://github.com/opendatateam/udata/pull/2672)
- New way of fixtures generation [#2677](https://github.com/opendatateam/udata/pull/2677):
  - The command now uses a remote file (default) if a URL is provided or a local one if a path is provided.
  - This file can be generated by using the command `generate-fixtures-file`, which takes as an argument the URL of the source queried to retieve the data dumped to the file.
  - The command `generate-fixtures-file` uses a customizable list of datasets slugs to know which datasets to query.
- Fixed the Geomform check for a GeoZone instance in formdata [#2683](https://github.com/opendatateam/udata/pull/2683)

## 3.2.1 (2021-10-22)

- Fix default sort with right sort column creation date name, for posts in back-office editorial page [#2665](https://github.com/opendatateam/udata/pull/2665)
- Meta read-only-enabled is back [#2664](https://github.com/opendatateam/udata/pull/2664)
- First endpoints for APIv2! Add datasets hateoas and resources pagination endpoints [#2663](https://github.com/opendatateam/udata/pull/2663) [#2667](https://github.com/opendatateam/udata/pull/2667)
- Add `archived` and `resources_count` fields in the dataset catalog [#2668](https://github.com/opendatateam/udata/pull/2668)

## 3.2.0 (2021-09-14)

- Update dependencies following setuptools 58.0.2 release that drop support for `use_2to3` [#2660](https://github.com/opendatateam/udata/pull/2660):
  - :warning: **breaking change** `rdfs` is not supported anymore
  - `jsonld` endpoints have a `@context` dict directly instead of an url to the context endpoint
- Update documentation with [udata-front plugin renaming](https://github.com/etalab/data.gouv.fr/issues/393) [#2661](https://github.com/opendatateam/udata/pull/2661)
- Various DCAT fixes (geonetwork compatibility) and debug command [#2662](https://github.com/opendatateam/udata/pull/2662)

## 3.1.0 (2021-08-31)

- :warning: Use pip-tools for requirements management [#2642](https://github.com/opendatateam/udata/pull/2642)[#2650](https://github.com/opendatateam/udata/pull/2650)[#2651](https://github.com/opendatateam/udata/pull/2651). Please [read the doc](https://github.com/opendatateam/udata/blob/master/docs/development-environment.md#python-and-virtual-environment) if you are a udata developer.
- :warning: Check db integrity and apply temporary and permanent fixes [#2644](https://github.com/opendatateam/udata/pull/2644) :warning: the associated migrations can take a long time to run.
- :warning: Upgrade to Flask-1.1.4 [#2639](https://github.com/opendatateam/udata/pull/2639)
- Safeguard `User.delete()` [#2646](https://github.com/opendatateam/udata/pull/2646)
- Fix user delete command [#2647](https://github.com/opendatateam/udata/pull/2647)
- Protect `test_ignore_post_save_signal` from weak ref error while testing [#2649](https://github.com/opendatateam/udata/pull/2649)
- Update translations following frontend refactoring (a lot of translations have been moved to udata-gouvfr) [#2648](https://github.com/opendatateam/udata/pull/2648)
- Fix RDF output content negociation [#2652](https://github.com/opendatateam/udata/pull/2652)
- Update Pillow dependency to 8.0.0 [#2654](https://github.com/opendatateam/udata/pull/2654)
- Add more fixes on HarvestSource and HarvestJobs for db integrity [#2653](https://github.com/opendatateam/udata/pull/2653/files)

## 3.0.4 (2021-08-12)

- Now returning notfound() http exception when router does not match any territory object instead of None [#2637](https://github.com/opendatateam/udata/pull/2637)
- Add larger reuse thumbnail image [#2638](https://github.com/opendatateam/udata/pull/2638)
- Activate plugins before creating app when testing [#2643](https://github.com/opendatateam/udata/pull/2643)

## 3.0.3 (2021-07-30)

- Remove mail sending task on follow [#2635](https://github.com/opendatateam/udata/pull/2635)
- Fix root api endpoint error [#2636](https://github.com/opendatateam/udata/pull/2636)

## 3.0.2 (2021-07-19)

- Fix sentry id event logging [#2364](https://github.com/opendatateam/udata/pull/2634)
- Fix remote resource upload [#2632](https://github.com/opendatateam/udata/pull/2632)

## 3.0.1 (2021-07-09)

- Remove apidoc blueprint, moved to udata-gouvfr [#2628](https://github.com/opendatateam/udata/pull/2628)
- New migration to update community resources schema from string to dict [#2629](https://github.com/opendatateam/udata/pull/2629)

## 3.0.0 (2021-07-07)

- :warning: **breaking change**: most of the theme/templates logic has been moved to https://github.com/etalab/udata-gouvfr. `udata` no longer contains a default theme. In the 3.x series, we hope it will be usable as a "headless" open data platform, but for now you probably need to plug your own theme or use udata-gouvfr. [More info about this change here](https://github.com/opendatateam/udata/blob/master/docs/roadmap/udata-3.md#the-road-to-udata3). [#2522](https://github.com/opendatateam/udata/pull/2522)
- Migrate from raven to sentry-sdk [#2620](https://github.com/opendatateam/udata/pull/2620)
- Add a UdataCleaner class to use udata's markdown configuration on SafeMarkup as well [#2619](https://github.com/opendatateam/udata/pull/2619)
- Fix schema name display in resource modal [#2617](https://github.com/opendatateam/udata/pull/2617)

## 2.7.1 (2021-05-27)

- Add migration to roolback on resource's schema's name to None [#2615](https://github.com/opendatateam/udata/pull/2615)

## 2.7.0 (2021-05-25)

- Modify `schema` field to resource. This field is now a nested field containing two sub-properties `name` and `version` [#2600](https://github.com/opendatateam/udata/pull/2600).
- Add a `schema_version` facet to the dataset search (need to be reindex to appear in results) [#2600](https://github.com/opendatateam/udata/pull/2600).

## 2.6.5 (2021-05-19)

- Fix create user by API [#2609](https://github.com/opendatateam/udata/pull/2609)
- Add sqlite, db and ics to allowed extensions [#2610](https://github.com/opendatateam/udata/pull/2610)
- Better markup parsing [#2611](https://github.com/opendatateam/udata/pull/2611):
  - Geozone's and Resource type's labelize function return None if no object is found.
  - New SafeMarkup class, which inherits from Markup, uses Bleach to sanitize Markup class.

## 2.6.4 (2021-03-24)

- Enhance self endpoint verification [#2604](https://github.com/opendatateam/udata/pull/2604)

## 2.6.3 (2021-03-23)

- Extraction of translation's strings [#2602](https://github.com/opendatateam/udata/pull/2602)

## 2.6.2 (2021-03-22)

- Fix SECURITY_CONFIRMABLE=False [#2588](https://github.com/opendatateam/udata/pull/2588)
- Support dct:license on DCAT harvester [#2589](https://github.com/opendatateam/udata/pull/2589)
- Admin small enhancements [#2591](https://github.com/opendatateam/udata/pull/2591):
  - The sidebar "Me" label has been renamed "Profile"
  - The user's profile now displays the user's email
  - The button "Edit" and the dropdown were merged. The button is now only a dropdown listing the actions.
  - "Edit" action has been renamed to "Edit the dataset/reuse/organization/profile" according to the current object to edit.
- Add `nofollow` attribute to links in discussions comments [#2593](https://github.com/opendatateam/udata/pull/2593)
- Add pip upgrade in circle's publish step [#2596](https://github.com/opendatateam/udata/pull/2596)
- Pin Twine's version [#2597](https://github.com/opendatateam/udata/pull/2597)
- Pin twine'version in circle's publish step [#2598](https://github.com/opendatateam/udata/pull/2598)

## 2.6.1 (2021-01-26)

- Fix url_for method in organization's catalog's view [#2587](https://github.com/opendatateam/udata/pull/2587)

## 2.6.0 (2021-01-25)

- Add resource's description and title size limit [#2586](https://github.com/opendatateam/udata/pull/2586)
- Add RDF catalog view for organizations [#2583](https://github.com/opendatateam/udata/pull/2583)

## 2.5.1 (2020-12-31)

- Add title's and description's length limit in forms [#2585](https://github.com/opendatateam/udata/pull/2585)

## 2.5.0 (2020-11-30)

- Change reuse's form's label name to title [#2575](https://github.com/opendatateam/udata/pull/2575)
- Unpublished posts are no longer served by the `Post.list` API endpoint [#2578](https://github.com/opendatateam/udata/pull/2578)
- Read only mode can now be toggled in settings [#2565](https://github.com/opendatateam/udata/pull/2565):
  - Toggles a warning banner on the frontend view and a warning toast on the admin view.
  - Prevents new users to register.
  - Prevents non admin users to create new content such as organizations, datasets, community resources or discussions.
  - Will return a `423` response code to any non-admin request to endpoints specified in `METHOD_BLOCKLIST` setting.
  - Existing content can still be updated.
- Add an alert block in layout template, to be overrided in installed theme [#2580](https://github.com/opendatateam/udata/pull/2580)

## 2.4.1 (2020-11-09)

- Escaping XML's forbidden characters [#2562](https://github.com/opendatateam/udata/pull/2562)
- Ignore pattern feature for linkchecker [#2564](https://github.com/opendatateam/udata/pull/2564)
- Fix TypeError when creating a superuser with an incorrect password [#2567](https://github.com/opendatateam/udata/pull/2567)

## 2.4.0 (2020-10-16)

- :warning: Resources and community resources creation API change [#2545](https://github.com/opendatateam/udata/pull/2545):
  - Remove the RESOURCES_FILE_ALLOWED_DOMAINS setting and mechanism.
  - The community resource's/resource's url could be set from the client side, even in the case of a hosted one, which is illogical.
    A hosted community resource's/resource's url should only be the sole responsibility of the backend.
  - Consequently, the POST endpoint of the community resources/resources API is only meant for the remote ones and the PUT endpoint of the community resources/resources API will take the existing resource's url to override the one sent by the client.
- Community resources changes [#2546](https://github.com/opendatateam/udata/pull/2546):
  - Dataset is now correctly set at community resource creation
  - Remove now useless job 'purge-orphan-community-resources'
- Using the fs_filename logic when uploading a new resource on the data catalog.[#2547](https://github.com/opendatateam/udata/pull/2547)
- Remove old file when updating resources and community resources from API [#2548](https://github.com/opendatateam/udata/pull/2548)
- Sortable.js upgrade to fix an issue in udata's editorial page when reordering featured datasets [#2550](https://github.com/opendatateam/udata/pull/2550)
- Password rotation mechanism [#2551](https://github.com/opendatateam/udata/pull/2551):
  - Datetime fields `password_rotation_demanded` and `password_rotation_performed` added to user model.
  - Override Flask-Security's login and reset password forms to implement the password rotation checks.
- Password complexity settings hardening [#2554](https://github.com/opendatateam/udata/pull/2554)
- Migrate ODS datasets urls [#2559](https://github.com/opendatateam/udata/pull/2559)

## 2.3.0 (2020-09-29)

- Plugin's translations are now correctly loaded [#2529](https://github.com/opendatateam/udata/pull/2529)
- Vine version is now pinned in requirements [#2532](https://github.com/opendatateam/udata/pull/2532)
- Fix reuses metrics [#2531](https://github.com/opendatateam/udata/pull/2531):
  - Reuses "datasets" metrics are now triggered correctly
  - New job to update the datasets "reuses" metrics: `update-datasets-reuses-metrics` to be scheduled
- Add a migration to set the reuses datasets metrics to the correct value [#2540](https://github.com/opendatateam/udata/pull/2540)
- Add a specific dataset's method for resource removal [#2534](https://github.com/opendatateam/udata/pull/2534)
- Flask-Security update [#2535](https://github.com/opendatateam/udata/pull/2535):
  - Switch to fork Flask-Security-Too
  - New settings to set the required password length and complexity
- Fix Flask-security sendmail overriding [#2536](https://github.com/opendatateam/udata/pull/2536)
- Add a custom password complexity checker to Flask-Security [#2537](https://github.com/opendatateam/udata/pull/2537)
- Change too short password error message [#2538](https://github.com/opendatateam/udata/pull/2538)

## 2.2.1 (2020-08-25)

- Some fixes for the static files deletion [#2526](https://github.com/opendatateam/udata/pull/2526):
  - New static files migration replacing the older one:
    - The migration now uses FS_URL.
    - Fixed the fs_filename string formating.
    - Now checks the community ressource's URLs too.
  - Removing the deletion script link in the CHANGELOG previous entry.
- Add a schema facet to the dataset search 🚧 requires datasets reindexation [#2523](https://github.com/opendatateam/udata/pull/2523)

## 2.2.0 (2020-08-05)

- CORS are now handled by Flask-CORS instead of Flask-RestPlus[#2485](https://github.com/opendatateam/udata/pull/2485)
- Oauth changes [#2510](https://github.com/opendatateam/udata/pull/2510):
  - Authorization code Grant now support PKCE flow
  - New command to create an OAuth client
  - :warning: Implicit grant is no longer supported
- :warning: Deletion workflow changes [#2488](https://github.com/opendatateam/udata/pull/2488):
  - Deleting a resource now triggers the deletion of the corresponding static file
  - Deleting a dataset now triggers the deletion of the corresponding resources (including community resources) and their static files
  - Adding a celery job `purge-orphan-community-resources` to remove community resources not linked to a dataset. This should be scheduled regularly.
  - Adding a migration file to populate resources fs_filename new field. Deleting the orphaned files is pretty deployment specific.
    A custom script should be writen in order to find and delete those files.
- Show traceback for migration errors [#2513](https://github.com/opendatateam/udata/pull/2513)
- Add `schema` field to ressources. This field can be filled based on an external schema catalog [#2512](https://github.com/opendatateam/udata/pull/2512)
- Add 2 new template hooks: `base.modals` (base template) and `dataset.resource.card.extra-buttons` (dataset resource card) [#2514](https://github.com/opendatateam/udata/pull/2514)

## 2.1.3 (2020-06-29)

- Fix internal links in markdown when not starting w/ slash [#2500](https://github.com/opendatateam/udata/pull/2500)
- Fix JS error when uploading a resource in certain conditions [#2483](https://github.com/opendatateam/udata/pull/2483)

## 2.1.2 (2020-06-17)

- Decoded api key byte string [#2482](https://github.com/opendatateam/udata/pull/2482)
- Removed now useless metric fetching [#2482](https://github.com/opendatateam/udata/pull/2484)
- Fix bug in harvester's cron schedule [#2493](https://github.com/opendatateam/udata/pull/2493)
- Adding banner options in settings for a potential use in an udata's theme [#2492](https://github.com/opendatateam/udata/pull/2492)

## 2.1.1 (2020-06-16)

- Broken release, use 2.1.2

## 2.1.0 (2020-05-12)

### Breaking changes

- Full metrics refactoring [2459](https://github.com/opendatateam/udata/pull/2459):
  - Metric collection is now useless and will not be filled anymore, you can remove it or keep it for archival sake. It will not be automatically removed.
  - [udata-piwik](https://github.com/opendatateam/udata-piwik) now uses InfluxDB as a buffer for trafic data before injecting them into udata's models.
  - Most of celery's tasks related to metrics are removed, this should help performance-wise on a big instance.
  - Charts related to metrics are removed from admin and dashboard panel until we have accurate data to populate them.
  - Site's metrics computation are not triggered by signals anymore.
  - A specific celery job needs to be run periodically to compute site's metrics.

### New features

- Nothing yet

## 2.0.4 (2020-05-04)

- Fix export-csv command (py3 compat) [#2472](https://github.com/opendatateam/udata/pull/2472)

## 2.0.3 (2020-04-30)

- :warning: Security fix: fix XSS in markdown w/ length JS filter [#2471](https://github.com/opendatateam/udata/pull/2471)

## 2.0.2 (2020-04-07)

- :warning: Breaking change / security fix: disallow html tags in markdown-it (JS markdown rendering) [#2465](https://github.com/opendatateam/udata/pull/2465)

## 2.0.1 (2020-03-24)

- Allow images to be displayed in markdown by default [#2462](https://github.com/opendatateam/udata/pull/2462)
- Fix deleted user's authentication on backend side [#2460](https://github.com/opendatateam/udata/pull/2460)

## 2.0.0 (2020-03-11)

### Breaking changes

- Migration to Python 3.7 [#1766](https://github.com/opendatateam/udata/pull/1766)
- The new migration system ([#1956](https://github.com/opendatateam/udata/pull/1956)) uses a new python based format. Pre-2.0 migrations are not compatible so you might need to upgrade to the latest `udata` version `<2.0.0`, execute migrations and then upgrade to `udata` 2+.
- The targeted mongo version is now Mongo 3.6. Backward support is not guaranteed
- Deprecated celery tasks have been removed, please ensure all old-style tasks (pre 1.6.20) have been consumed before migrating [#2452](https://github.com/opendatateam/udata/pull/2452)

### New features

- New migration system [#1956](https://github.com/opendatateam/udata/pull/1956):
  - Use python based migrations instead of relying on mongo internal and deprecated `js_exec`
  - Handle rollback (optionnal)
  - Detailled history
- Template hooks generalization: allows to dynamically extend template with widgets and snippets from extensions. See [the dedicated documentation section](https://udata.readthedocs.io/en/stable/extending/#hooks) [#2323](https://github.com/opendatateam/udata/pull/2323)
- Markdown now supports [Github Flavored Markdown (GFM) specs](https://github.github.com/gfm/) (ie. the already supported [CommonMark specs](https://spec.commonmark.org) plus tables, strikethrough, autolinks support and predefined disallowed raw HTML) [#2341](https://github.com/opendatateam/udata/pull/2341)

## 1.6.20 (2020-01-21)

- New Crowdin translations [#2360](https://github.com/opendatateam/udata/pull/2360)
- Fix territory routing for @latest [#2447](https://github.com/opendatateam/udata/pull/2447)
- Refactor Celery: py2/py3 compatibility, use ids as payload [#2305](https://github.com/opendatateam/udata/pull/2305)
- Automatically archive dangling harvested datasets :warning: this is enabled by default [#2368](https://github.com/opendatateam/udata/pull/2368)
- Refactor celery tasks to avoid models/documents in the transport layer [#2305](https://github.com/opendatateam/udata/pull/2305)

## 1.6.19 (2020-01-06)

- `rel=nofollow` on remote source links [#2364](https://github.com/opendatateam/udata/pull/2364)
- Fix admin messages and fix user roles selector default value [#2365](https://github.com/opendatateam/udata/pull/2365)
- Fix new harvester's form tooltip showup [#2371](https://github.com/opendatateam/udata/pull/2371)
- Fix responsive design of search results [#2372](https://github.com/opendatateam/udata/pull/2372)
- Fix non-unique ids in datasets' comments [#2374](https://github.com/opendatateam/udata/pull/2374)
- Case insensitive license matching [#2378](https://github.com/opendatateam/udata/pull/2378)

## 1.6.18 (2019-12-13)

- Remove embedded API doc [#2343](https://github.com/opendatateam/udata/pull/2343) :warning: Breaking change, please customize `API_DOC_EXTERNAL_LINK` for your needs.
- Removed published date from community ressources [#2350](https://github.com/opendatateam/udata/pull/2350)
- Added new size for avatars in user's model (`udata images render` must be run in order to update the size of existing images) [#2353](https://github.com/opendatateam/udata/pull/2353)
- Fixed user's avatar change [#2351](https://github.com/opendatateam/udata/issues/2351)
- Removed dead code [#2355](https://github.com/opendatateam/udata/pull/2355)
- Resolved conflict between id and slug [#2356](https://github.com/opendatateam/udata/pull/2356)
- Fix next link in posts pagination [#2358](https://github.com/opendatateam/udata/pull/2358)
- Fix organization's members roles translation [#2359](https://github.com/opendatateam/udata/pull/2359)
## 1.6.17 (2019-10-28)

- Disallow URLs in first and last names [#2345](https://github.com/opendatateam/udata/pull/2345)

## 1.6.16 (2019-10-22)

- Prevent Google ranking spam attacks on reuse pages (`rel=nofollow` on reuse link) [#2320](https://github.com/opendatateam/udata/pull/2320)
- Display admin resources list actions only if user has permissions to edit [#2326](https://github.com/opendatateam/udata/pull/2326)
- Fix non-admin user not being able to change their profile picture [#2327](https://github.com/opendatateam/udata/pull/2327)

## 1.6.15 (2019-09-11)

- Style links in admin modals [#2292](https://github.com/opendatateam/udata/pull/2292)
- Add activity.key filter to activity.atom feed [#2293](https://github.com/opendatateam/udata/pull/2293)
- Allow `Authorization` as CORS header and OAuth minor fixes [#2298](https://github.com/opendatateam/udata/pull/2298)
- Set dataset.private to False by default (and fix stock) [#2307](https://github.com/opendatateam/udata/pull/2307)
- Fixes some inconsistencies between admin display (buttons, actions...) and real permissions [#2308](https://github.com/opendatateam/udata/pull/2308)


## 1.6.14 (2019-08-14)

- Cleanup `permitted_reuses` data (migration) [#2244](https://github.com/opendatateam/udata/pull/2244)
- Proper form errors handling on nested fields [#2246](https://github.com/opendatateam/udata/pull/2246)
- JS models load/save/update consistency (`loading` always `true` on query, always handle error, no more silent errors) [#2247](https://github.com/opendatateam/udata/pull/2247)
- Ensures that date ranges are always positive (ie. `start` < `end`) [#2253](https://github.com/opendatateam/udata/pull/2253)
- Enable completion on the "`MIME type`" resource form field (needs reindexing) [#2238](https://github.com/opendatateam/udata/pull/2238)
- Ensure oembed rendering errors are not hidden by default error handlers and have cors headers [#2254](https://github.com/opendatateam/udata/pull/2254)
- Handle dates before 1900 during indexing [#2256](https://github.com/opendatateam/udata/pull/2256)
- `spatial load` command is more resilient: make use of a temporary collection when `--drop` option is provided (avoid downtime during the load), in case of exception or keybord interrupt, temporary files and collections are cleaned up [#2261](https://github.com/opendatateam/udata/pull/2261)
- Configurable Elasticsearch timeouts. Introduce `ELASTICSEARCH_TIMEOUT` as default/read timeout and `ELASTICSEARCH_INDEX_TIMEOUT` as indexing/write timeout [#2265](https://github.com/opendatateam/udata/pull/2265)
- OEmbed support for organizations [#2273](https://github.com/opendatateam/udata/pull/2273)
- Extract search parameters as settings allowing fine tuning search without repackaging udata (see [the **Search configuration** documentation](https://udata.readthedocs.io/en/stable/adapting-settings/#search-configuration)) [#2275](https://github.com/opendatateam/udata/pull/2275)
- Prevent `DoesNotExist` error in activity API: silence the error for the consumer but log it (ie. visible in Sentry) [#2268](https://github.com/opendatateam/udata/pull/2268)
- Optimize CSV export generation memory wise [#2277](https://github.com/opendatateam/udata/pull/2277)

## 1.6.13 (2019-07-11)

- Rename og:image target :warning: this will break your custom theme, please rename your logo image file to `logo-social.png` instead of `logo-600x600.png` [#2217](https://github.com/opendatateam/udata/pull/2217)
- Don't automatically overwrite `last_update` field if manually set [#2020](https://github.com/opendatateam/udata/pull/2220)
- Spatial completion: only index last version of each zone and prevent completion cluttering [#2140](https://github.com/opendatateam/udata/pull/2140)
- Init: prompt to loads countries [#2140](https://github.com/opendatateam/udata/pull/2140)
- Handle UTF-8 filenames in `spatial load_logos` command [#2223](https://github.com/opendatateam/udata/pull/2223)
- Display the datasets, reuses and harvesters deleted state on listing when possible [#2228](https://github.com/opendatateam/udata/pull/2228)
- Fix queryless (no `q` text parameter) search results scoring (or lack of scoring) [#2231](https://github.com/opendatateam/udata/pull/2231)
- Miscellaneous fixes on completers [#2215](https://github.com/opendatateam/udata/pull/2215)
- Ensure `filetype='remote'` is set when using the manual ressource form [#2236](https://github.com/opendatateam/udata/pull/2236)
- Improve harvest sources listing (limit `last_job` fetched and serialized fields, reduce payload) [#2214](https://github.com/opendatateam/udata/pull/2214)
- Ensure HarvestItems are cleaned up on dataset deletion [#2214](https://github.com/opendatateam/udata/pull/2214)
- Added `config.HARVEST_JOBS_RETENTION_DAYS` and a `harvest-purge-jobs` job to apply it [#2214](https://github.com/opendatateam/udata/pull/2214) (migration). **Warning, the migration will enforce `config.HARVEST_JOBS_RETENTION_DAYS` and can take some time on a big `HarvestJob` collection**
- Drop `no_dereference` on indexing to avoid the "`dictionary changed size during iteration`" error until another solution is found. **Warning: this might result in more resources consumption while indexing** [#2237](https://github.com/opendatateam/udata/pull/2237)
- Fix various issues around discussions UI [#2190](https://github.com/opendatateam/udata/pull/2190)


## 1.6.12 (2019-06-26)

- Archive dataset feature [#2172](https://github.com/opendatateam/udata/pull/2172)
- Refactor breadcrum includes [#2173](https://github.com/opendatateam/udata/pull/2173)
- Better dependencies management [#2182](https://github.com/opendatateam/udata/pull/2182) and [#2172/install.pip](https://github.com/opendatateam/udata/pull/2172/files#diff-d7b45472f3465d62f857d14cf59ea8a2)
- Reduce following to staring [#2192](https://github.com/opendatateam/udata/pull/2192/files)
- Simplify display of spatial coverage in search results [#2192](https://github.com/opendatateam/udata/pull/2192/files)
- Add cache for organization and topic display pages [#2194](https://github.com/opendatateam/udata/pull/2194)
- Dataset of datasets: id as ref instead of slug [#2195](https://github.com/opendatateam/udata/pull/2195) :warning: this introduces some settings changes, cf [documentation for EXPORT_CSV](https://github.com/opendatateam/udata/blob/master/docs/adapting-settings.md).
- Add meta og:type: make twitter cards work [#2196](https://github.com/opendatateam/udata/pull/2196)
- Fix UI responsiveness [#2199](https://github.com/opendatateam/udata/pull/2199)
- Remove social media sharing feature [#2200](https://github.com/opendatateam/udata/pull/2200)
- Quick fix for activity.atom [#2203](https://github.com/opendatateam/udata/pull/2203)
- Remove diff from js dependencies to fix CVE [#2204](https://github.com/opendatateam/udata/pull/2204)
- Replace default sort label for better readability [#2206](https://github.com/opendatateam/udata/pull/2206)
- Add a condition to up-to-dateness of a dataset [#2208](https://github.com/opendatateam/udata/pull/2208)
- Prevent deleted harvesters from running until purged. Harvest jobs history is deleted too on purge. [#2209](https://github.com/opendatateam/udata/pull/2209)
- Better quality.frequency management [#2211](https://github.com/opendatateam/udata/pull/2211)
- Fix caching of topic pages [#2213](https://github.com/opendatateam/udata/pull/2213)

## 1.6.11 (2019-05-29)

- Center incomplete rows of cards [#2162](https://github.com/opendatateam/udata/pull/2162)
- Allow .dxf upload [#2164](https://github.com/opendatateam/udata/pull/2164)
- Always use remote_url as harvesting source [#2165](https://github.com/opendatateam/udata/pull/2165)
- Update jquery to ~3.4.1 [#2161](https://github.com/opendatateam/udata/pull/2161)
- Fix various issues with search result page [#2166](https://github.com/opendatateam/udata/pull/2166)
- Restore notbroken facet includes [#2169](https://github.com/opendatateam/udata/pull/2169)

## 1.6.10 (2019-05-23)

- Remove `<br>` in badge display [#2156](https://github.com/opendatateam/udata/pull/2156)
- Display user avatar and fix its sizing [#2157](https://github.com/opendatateam/udata/pull/2157)
- Redirect unfiltered csv exports to dataset of datasets [#2158](https://github.com/opendatateam/udata/pull/2158)
- Show organization id in a modal and add hyperlinks to ids in detail modal [#2159](https://github.com/opendatateam/udata/pull/2159)

## 1.6.9 (2019-05-20)

- Add user slug to dataset cache key [#2146](https://github.com/opendatateam/udata/pull/2146)
- Change display of cards of reuses on topic pages [#2148](https://github.com/opendatateam/udata/pull/2148)
- Display remote source of harvested dataset [#2150](https://github.com/opendatateam/udata/pull/2150)
- Prefill community resource type on upload form [#2151](https://github.com/opendatateam/udata/pull/2151)
- Fix user profile UI [#2152](https://github.com/opendatateam/udata/pull/2152)
- Remove concept of permitted reuse [#2153](https://github.com/opendatateam/udata/pull/2153)

## 1.6.8 (2019-05-13)

- Configurable search autocomplete [#2138](https://github.com/opendatateam/udata/pull/2138)

## 1.6.7 (2019-05-10)

- Refactor DCAT harvesting to store only one graph (and prevent MongoDB document size overflow) [#2096](https://github.com/opendatateam/udata/pull/2096)
- Expose sane defaults for `TRACKING_BLACKLIST` [#2098](https://github.com/opendatateam/udata/pull/2098)
- Bubble up uploader errors [#2102](https://github.com/opendatateam/udata/pull/2102)
- Ensure `udata worker status --munin` always outputs zero values so munin won't see it has a "no data" response [#2103](https://github.com/opendatateam/udata/pull/2103)
- Metrics tuning: breaks circular dependencies, drop exec_js/eval usage, proper logging... [#2113](https://github.com/opendatateam/udata/pull/2113)
- Change reuse icon from "retweet" to "recycle" [#2122](https://github.com/opendatateam/udata/pull/2122)
- Admins can delete a single comment in a discussion thread [#2087](https://github.com/opendatateam/udata/pull/2087)
- Add cache directives to dataset display blocks [#2129](https://github.com/opendatateam/udata/pull/2129)
- Export multiple models objects to CSV (dataset of datasets) [#2124](https://github.com/opendatateam/udata/pull/2124)


## 1.6.6 (2019-03-27)

- Automatically loads default settings from plugins (if `plugin.settings` module exists) [#2058](https://github.com/opendatateam/udata/pull/2058)
- Fixes some memory leaks on reindexing [#2070](https://github.com/opendatateam/udata/pull/2070)
- Fixes minor UI bug [#2072](https://github.com/opendatateam/udata/pull/2072)
- Prevent ExtrasField failure on null value [#2074](https://github.com/opendatateam/udata/pull/2074)
- Improve ModelField errors handling [#2075](https://github.com/opendatateam/udata/pull/2075)
- Fix territories home map [#2077](https://github.com/opendatateam/udata/pull/2077)
- Prevent timeout on `udata index` in some cases [#2079](https://github.com/opendatateam/udata/pull/2079)
- Pin werkzeug dependency to `0.14.1` until incompatibilities are fixed [#2081](https://github.com/opendatateam/udata/pull/2081)
- Prevent client-side error while handling unparseable API response [#2076](https://github.com/opendatateam/udata/pull/2076)
- Fix the `udata job schedule` erroneous help message [#2083](https://github.com/opendatateam/udata/pull/2083)
- Fix upload button on replace resource file [#2085](https://github.com/opendatateam/udata/pull/2085)
- Ensure harvest items statuses are updated on the right job [#2089](https://github.com/opendatateam/udata/pull/2089)
- Added Serbian translations [#2055](https://github.com/opendatateam/udata/pull/2055)

## 1.6.5 (2019-02-27)

- Replace "An user" by "A user" [#2033](https://github.com/opendatateam/udata/pull/2033)
- Use "udata" and fix a few other typos in documentation and UI/translation strings [#2023](https://github.com/opendatateam/udata/pull/2023)
- Add a surrounding block declaration around community section [2039](https://github.com/opendatateam/udata/pull/2039)
- Fix broken form validation on admin discussions and issues [#2045](https://github.com/opendatateam/udata/pull/2045)
- Fix full reindexation by avoiding `SlugField.instance` deepcopy in `no_dereference()` querysets [#2048](https://github.com/opendatateam/udata/pull/2048)
- Ensure deleted user slug is pseudonymized [#2049](https://github.com/opendatateam/udata/pull/2049)
- Prevent the "Add resource" modal from closing when using the frontend "Add resource" button [#2052](https://github.com/opendatateam/udata/pull/2052)

## 1.6.4 (2019-02-02)

- Fix workers: pin redis version for Celery compatibility [#2019](https://github.com/opendatateam/udata/pull/2019)

## 1.6.3 (2019-02-01)

- Remove extra attributes on user deletion [#1961](https://github.com/opendatateam/udata/pull/1961)
- Pin phantomjs to version `2.1.7` [#1975](https://github.com/opendatateam/udata/pull/1975)
- Protect membership accept route against flood [#1984](https://github.com/opendatateam/udata/pull/1984)
- Ensure compatibility with IE11 and Firefox ESR [#1990](https://github.com/opendatateam/udata/pull/1990)
- Lots of fixes on the resource form. Be explicit about uploading a new file [#1991](https://github.com/opendatateam/udata/pull/1991)
- Centralize `selectize` handling and style in `base-completer` and apply some fixes [1992](https://github.com/opendatateam/udata/pull/1992)
- Added the missing `number` input field widget [#1993](https://github.com/opendatateam/udata/pull/1993)
- Fix the organization private datasets and reuses counters [#1994](https://github.com/opendatateam/udata/pull/1994)
- Disable autocorrect, spellcheck... on search and completion fields [#1995](https://github.com/opendatateam/udata/pull/1995)
- Fix harvest preview in edit form not taking configuration (features and filters) [#1996](https://github.com/opendatateam/udata/pull/1996)
- Ensure organization page react to URL hash changes (including those from right sidebar) [#1997](https://github.com/opendatateam/udata/pull/1997)
- Updating community resource as admin keeps original owner [#1999](https://github.com/opendatateam/udata/pull/1999)
- Major form fixes [#2000](https://github.com/opendatateam/udata/pull/2000)
- Improved admin errors handling: visual feedback on all errors, `Sentry-ID` header if present, hide organization unauthorized actions [#2005](https://github.com/opendatateam/udata/pull/2005)
- Expose and import licenses `alternate_urls` and `alternate_titles` fields [#2006](https://github.com/opendatateam/udata/pull/2006)
- Be consistent on search results wording and icons (Stars vs Followers) [#2013](https://github.com/opendatateam/udata/pull/2013)
- Switch from a "full facet reset" to a "by term reset" approach in search facets [#2014](https://github.com/opendatateam/udata/pull/2014)
- Ensures all modals have the same buttons styles and orders, same color code... [#2012](https://github.com/opendatateam/udata/pull/2012)
- Ensure URLs from assets stored on `CDN_DOMAINS` are considered as valid and that associated error message is properly translated [#2017](https://github.com/opendatateam/udata/pull/2017)

## 1.6.2 (2018-11-05)

- Display the owner/organization on harvester view [#1921](https://github.com/opendatateam/udata/pull/1921)
- Improve harvest validation errors handling [#1920](https://github.com/opendatateam/udata/pull/1920)
- Make extra TOS text customizable [#1922](https://github.com/opendatateam/udata/pull/1922)
- Fixes an `UnicodeEncodeError` occuring when parsing RDF with unicode URLs [#1919](https://github.com/opendatateam/udata/pull/1919)
- Fix some external assets handling cases [#1918](https://github.com/opendatateam/udata/pull/1918)
- Harvest items can now match `source.id` before `source.domain` — no more duplicates when changing an harvester URL [#1923](https://github.com/opendatateam/udata/pull/1923)
- Ensure image picker/cropper only allows images [#1925](https://github.com/opendatateam/udata/pull/1925)
- Make tags min and max length configurable and ensure admin takes its configuration from the backend [#1935](https://github.com/opendatateam/udata/pull/1935)
- Prevent errors when there is no date available to focus on the calendar [#1937](https://github.com/opendatateam/udata/pull/1937)

### Internals

- Update authlib to 0.10 [#1916](https://github.com/opendatateam/udata/pull/1916)

## 1.6.1 (2018-10-11)

- Allows arguments and keyword arguments in the task `@connect` decorator [#1908](https://github.com/opendatateam/udata/pull/1908)
- Allows to restore assets after being deleted (Datasets, Organizations and Reuses) [#1901](https://github.com/opendatateam/udata/pull/1901)
- Fixes form events not bubbling (and so fixes harvester config not displaying) [#1914](https://github.com/opendatateam/udata/pull/1914)

## 1.6.0 (2018-10-02)

### New features

- Harvest sources are now filterable through the harvest source create/edit admin form [#1812](https://github.com/opendatateam/udata/pull/1812)
- Harvest sources can now enable or disable some optional backend features [#1875](https://github.com/opendatateam/udata/pull/1875)
- Post UIs have been reworked: publication date, publish/unpublish action, save and continue editing, dynamic sidebar, alignments fixes... [#1857](https://github.com/opendatateam/udata/pull/1857)

### Minor changes

- Only display temporal coverage years on cards and search results [#1833](https://github.com/opendatateam/udata/pull/1833)
- Add publisher's name on dataset template [#1847](https://github.com/opendatateam/udata/pull/1847)
- Improved upload error handling: deduplicate notifications, localized generic error message, sentry identifier... [#1842](https://github.com/opendatateam/udata/pull/1842)
- Allows to filter datasets on resource `type` (needs reindexing) [#1848](https://github.com/opendatateam/udata/pull/1848)
- Switch the admin sidebar collapse icon from "hamburger"to left and right arrows [#1855](https://github.com/opendatateam/udata/pull/1855)
- Discussion add card style coherence [#1884](https://github.com/opendatateam/udata/pull/1884)
- `LINKCHECKING_UNCHECKED_TYPES` setting to prevent linkchecking on some ressource types [#1892](https://github.com/opendatateam/udata/pull/1892)
- `swagger.json` API specifications now pass validation [#1898](https://github.com/opendatateam/udata/pull/1898)

### Breaking changes

- Static assets are now compatible with long-term caching (ie. their hash is present in the filename). :warning: On your development environment you need to run `inv assets-build` to generate an initial `manifest.json`, both in `udata` and in your theme extension if it uses manifest. See [#1826](https://github.com/opendatateam/udata/pull/1826) for full details.
- Theme are now responsible for adding their CSS markup on template (no more assumptions on `theme.css` and `admin.css`). Most of the time, overriding `raw.html` and `admin.html` should be sufficient
- The discussions API `posted_by` attribute is now an embedded user instead of an user ID to avoid extra API calls [#1839](https://github.com/opendatateam/udata/pull/1839)

### Bugfixes

- Hide the `resource.type` attribute from JSON-LD output until handled by a dedicated vocabulary/property [#1865](https://github.com/opendatateam/udata/pull/1865)
- RDFs, CSVs and resource redirect views are now handling CORS properly [#1866](https://github.com/opendatateam/udata/pull/1866)
- Fix broken sorts on organization's datasets list in admin [#1873](https://github.com/opendatateam/udata/pull/1873)
- Ensure harvest previewing is done against current form content [#1888](https://github.com/opendatateam/udata/pull/1888)
- Ensure deleted objects are unindexed [#1891](https://github.com/opendatateam/udata/pull/1891)
- Fix the dataset resources list layout wrapping [#1893](https://github.com/opendatateam/udata/pull/1893)
- Fix wrong behavior for weblinks [#1894](https://github.com/opendatateam/udata/pull/1894)
- Ensure `info config` command only displays configuration variables [#1897](https://github.com/opendatateam/udata/pull/1897)

### Internal

- Upgrade to Authlib 0.9 [#1760](https://github.com/opendatateam/udata/pull/1760) [#1827](https://github.com/opendatateam/udata/pull/1827)
- Add a `Dataset.on_resource_added` signal

## 1.5.3 (2018-08-27)

- Prevent UnicodeError on unicode URL validation error [#1844](https://github.com/opendatateam/udata/pull/1844)
- Hide save button in "Add resource" modal until form is visible (and prevent error) [#1846](https://github.com/opendatateam/udata/pull/1846)
- The purge chunks tasks also remove the directory [#1845](https://github.com/opendatateam/udata/pull/1845)
- Upgrade to latest Fine-Uploader version to benefit from bug fixes [#1849](https://github.com/opendatateam/udata/pull/1849)
- Prevent front views from downloading `swagger.json` [#1838](https://github.com/opendatateam/udata/pull/1838)
- Ensure API docs works without data [#1840](https://github.com/opendatateam/udata/pull/1840)
- Expose the default spatial granularity in API specs [#1841](https://github.com/opendatateam/udata/pull/1841)
- Fix missing dataset title on client-side card listing [#1834](https://github.com/opendatateam/udata/pull/1834)
- Allows to clear the dataset form temporal coverage. [#1832](https://github.com/opendatateam/udata/pull/1832)
- Ensure that admin notifications are displayed once and with a constant width. [#1831](https://github.com/opendatateam/udata/pull/1831)
- Fix broken date range picker date parsing (ie. manual keyboard input) [#1863](https://github.com/opendatateam/udata/pull/1853)
- Normalize uploaded filenames to avoid encoding issues, filesystem incompatibilities... [#1852](https://github.com/opendatateam/udata/pull/1852)

## 1.5.2 (2018-08-08)

- Fix client-side temporal coverage rendering [#1821](https://github.com/opendatateam/udata/pull/1821)
- Prevent word breaking when wrapping discussions messages [#1822](https://github.com/opendatateam/udata/pull/1822)
- Properly render message content on issues and discussions mails [#1823](https://github.com/opendatateam/udata/pull/1823)

## 1.5.1 (2018-08-03)

- Ensure OEmbed compatibility with external CDN [#1815](https://github.com/opendatateam/udata/pull/1815)
- Fixes some static URL serialization [#1815](https://github.com/opendatateam/udata/pull/1815)

## 1.5.0 (2018-07-30)

### New features

- Slugs are now redirected on change when changed until old slug are free [#1771](https://github.com/opendatateam/udata/pull/1771)
- Improve usability of new organization form [#1777](https://github.com/opendatateam/udata/pull/1777)
- Allows to serve assets on an external CDN domain using `CDN_DOMAIN` [#1804](https://github.com/opendatateam/udata/pull/1804)

### Breaking changes

None

### Bug fixes and minor changes

- Sort dataset update frequencies by ascending frequency [#1758](https://github.com/opendatateam/udata/pull/1758)
- Skip gov.uk references tests when site is unreachable [#1767](https://github.com/opendatateam/udata/pull/1767)
- Fix resources reorder (registered extras validation logic) [#1796](https://github.com/opendatateam/udata/pull/1796)
- Fix checksum display on resource modal [#1797](https://github.com/opendatateam/udata/pull/1797)
- Use metrics.views on resource card [#1778](https://github.com/opendatateam/udata/pull/1778)
- Fix dataset collapse on ie11 [#1802](https://github.com/opendatateam/udata/pull/1802)
- Upgrade i18next (security) [#1803](https://github.com/opendatateam/udata/pull/1803)

### Internals

- Backports some Python 3 forward compatible changes and fixes some bugs [#1769](https://github.com/opendatateam/udata/pull/1769):
    - avoid `filter` and `map` usage instead of list comprehension
    - explicit encoding handling
    - avoid comparison to `None`
    - use `next()` instead of `.next()` to iterate
    - unhide some implicit casts (in particular search weight)
- Tests are now run against `local.test` instead of `localhost` to avoid pytest warnings

## 1.4.1 (2018-06-15)

- Fix community resource creation and display [#1733](https://github.com/opendatateam/udata/pull/1733)
- Failsafe JS cache storage: use a custom in-memory storage as fallback when access to `sessionStorage` is not allowed [#1742](https://github.com/opendatateam/udata/pull/1742)
- Prevent errors when handling API errors without data/payload [#1743](https://github.com/opendatateam/udata/pull/1743)
- Improve/fix validation error formatting on harvesting [#1745](https://github.com/opendatateam/udata/pull/1745)
- Ensure daterange can be parsed from full iso datetime [#1748](https://github.com/opendatateam/udata/pull/1748)
- API: enforce application/json content-type for forms [#1751](https://github.com/opendatateam/udata/pull/1751)
- RDF parser can now process [european frequencies](https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency) [#1752](https://github.com/opendatateam/udata/pull/1752)
- Fix images upload broken by chunked upload [#1756](https://github.com/opendatateam/udata/pull/1756)

## 1.4.0 (2018-06-06)

### New features

- Typed resources [#1398](https://github.com/opendatateam/udata/issues/1398)
- Initial data preview implementation [#1581](https://github.com/opendatateam/udata/pull/1581) [#1632](https://github.com/opendatateam/udata/pull/1632)
- Handle some alternate titles and alternate URLs on licenses for improved match on harvesting [#1592](https://github.com/opendatateam/udata/pull/1592)
- Allow to specify a dataset acronym [#1217](https://github.com/opendatateam/udata/pull/1217)
- Starts using harvest backend `config` (validation, API exposition, `HarvestFilters`...) [#1716](https://github.com/opendatateam/udata/pull/1716)
- The map widget can now be configured (tiles URL, initial position...) [#1672](https://github.com/opendatateam/udata/pull/1672)
- New discussions layout [#1623](https://github.com/opendatateam/udata/pull/1623)
- Dynamic API documentation, Enhancement to Pull #1542 - [#1542](https://github.com/opendatateam/udata/pull/1542)
- Resource modal overhaul with markdown support [#1547](https://github.com/opendatateam/udata/pull/1547)

### Breaking changes

- Normalize resource.format (migration - :warning: need reindexing). [#1563](https://github.com/opendatateam/udata/pull/1563)
- Enforce a domain whitelist when resource.filetype is file. See [`RESOURCES_FILE_ALLOWED_DOMAINS`](https://udata.readthedocs.io/en/latest/adapting-settings/#resources_file_allowed_domains) settings variable for details and configuration. [#1567](https://github.com/opendatateam/udata/issues/1567)
- Remove extras from datasets search index (needs reindexation) [#1718](https://github.com/opendatateam/udata/pull/1718)

### Bug fixes and minor changes

- Switch to PyPI.org for package links [#1583](https://github.com/opendatateam/udata/pull/1583)
- Show resource type in modal (front) [#1714](https://github.com/opendatateam/udata/pull/1714)
- Adds ETag to internal avatar for efficient caching control [#1712](https://github.com/opendatateam/udata/pull/1712)
- Fix 404/missing css on front pages [#1709](https://github.com/opendatateam/udata/pull/1709)
- Fix markdown max image width (front) [#1707](https://github.com/opendatateam/udata/pull/1707)
- Ensure registered extras types are properly parsed from JSON. Remove the need for custom `db.Extra` classes [#1699](https://github.com/opendatateam/udata/pull/1699)
- Fix the temporal coverage facet query string parsing [#1676](https://github.com/opendatateam/udata/pull/1676)
- Fix search auto-complete hitbox [#1687](https://github.com/opendatateam/udata/pull/1687)
- Fix Firefox custom error handling, part 2 [#1671](https://github.com/opendatateam/udata/pull/1671)
- Add resend confirmation email link to login screen [#1653](https://github.com/opendatateam/udata/pull/1653)
- Audience metrics: use only `views` [#1607](https://github.com/opendatateam/udata/pull/1607)
- Add missing spatial granularities translations [#1636](https://github.com/opendatateam/udata/pull/1636)
- Protocol-relative URLs support [#1599](https://github.com/opendatateam/udata/pull/1599)

### Internals

- Simplify `ExtrasField` form field signature (no need anymore for the `extras` parameter) [#1698](https://github.com/opendatateam/udata/pull/1698)
- Register known extras types [#1700](https://github.com/opendatateam/udata/pull/1700)

## 1.3.12 (2018-05-31)

- Fix side menu on mobile [#1701](https://github.com/opendatateam/udata/pull/1701)
- Fix update frequency field [#1702](https://github.com/opendatateam/udata/pull/1702)

## 1.3.11 (2018-05-29)

- Protect Resource.need_check against malformed/string dates [#1691](https://github.com/opendatateam/udata/pull/1691)
- Fix search auto-complete loading on new page [#1693](https://github.com/opendatateam/udata/pull/1693)

## 1.3.10 (2018-05-11)

- Expose Resource.extras as writable in the API [#1660](https://github.com/opendatateam/udata/pull/1660)
- Fix Firefox custom errors handling [#1662](https://github.com/opendatateam/udata/pull/1662)

## 1.3.9 (2018-05-07)

- Prevent linkchecker to pollute timeline as a side-effect. (migration). **Warning, the migration will delete all dataset update activities** [#1643](https://github.com/opendatateam/udata/pull/1643)
- Fix OAuth authorization screen failing with unicode `SITE_TITLE` [#1624](https://github.com/opendatateam/udata/pull/1624)
- Fix markdown handling of autolinks with angle brackets and factorize (and test) markdown `parse_html()` [#1625](https://github.com/opendatateam/udata/pull/1625)
- Fix timeline order [#1642](https://github.com/opendatateam/udata/pull/1642)
- Fix markdown rendering on IE11 [#1645](https://github.com/opendatateam/udata/pull/1645)
- Consider bad UUID as 404 in routing [#1646](https://github.com/opendatateam/udata/pull/1646)
- Add missing email templates [#1647](https://github.com/opendatateam/udata/pull/1647)
- Polyfill `ChildNode.remove()` for IE11 [#1648](https://github.com/opendatateam/udata/pull/1648)
- Improve Raven-js/Sentry error handling [#1649](https://github.com/opendatateam/udata/pull/1649)
- Prevent regex special characters to break site search [#1650](https://github.com/opendatateam/udata/pull/1650)

## 1.3.8 (2018-04-25)

- Fix sendmail regression [#1620](https://github.com/opendatateam/udata/pull/1620)

## 1.3.7 (2018-04-24)

- Fix some search parameters validation [#1601](https://github.com/opendatateam/udata/pull/1601)
- Prevent API tracking errors with unicode [#1602](https://github.com/opendatateam/udata/pull/1602)
- Prevent a race condition error when uploading file with concurrent chunking [#1606](https://github.com/opendatateam/udata/pull/1606)
- Disallow resources dict in API [#1603](https://github.com/opendatateam/udata/pull/1603)
- Test and fix territories routing [#1611](https://github.com/opendatateam/udata/pull/1611)
- Fix the client-side Raven/Sentry configuration [#1612](https://github.com/opendatateam/udata/pull/1612)
- Raise a 404 in case of unknown RDF content type [#1613](https://github.com/opendatateam/udata/pull/1613)
- Ensure current theme is available to macros requiring it in mails [#1614](https://github.com/opendatateam/udata/pull/1614)
- Fix documentation about NGinx configuration for https [#1615](https://github.com/opendatateam/udata/pull/1615)
- Remove unwanted commas in default `SECURITY_EMAIL_SUBJECT_*` parameters [#1616](https://github.com/opendatateam/udata/pull/1616)

## 1.3.6 (2018-04-16)

- Prevent OEmbed card to be styled when loaded in bootstrap 4 [#1569](https://github.com/opendatateam/udata/pull/1569)
- Fix organizations sort by last_modified [#1576](https://github.com/opendatateam/udata/pull/1576)
- Fix dataset creation form (and any other form) [#1584](https://github.com/opendatateam/udata/pull/1584)
- Fix an XSS on client-side markdown parsing [#1585](https://github.com/opendatateam/udata/pull/1585)
- Ensure URLs validation is the same everywhere [#1586](https://github.com/opendatateam/udata/pull/1586)

## 1.3.5 (2018-04-03)

- Upgrade `sifter` to `0.5.3` [#1548](https://github.com/opendatateam/udata/pull/1548)
- Upgrade `jquery-validation` to 1.17.0 and fixes some issues with client-side URL validation [#1550](https://github.com/opendatateam/udata/pull/1550)
- Minor change on OEmbed cards to avoid theme to override the cards `font-family` [#1549](https://github.com/opendatateam/udata/pull/1549)
- Improve cli unicode handling [#1551](https://github.com/opendatateam/udata/pull/1551)
- Fix DCAT harvester mime type detection [#1552](https://github.com/opendatateam/udata/pull/1552)
- Add the missing harvester URL in admin [#1554](https://github.com/opendatateam/udata/pull/1554)
- Fix harvester preview/job layout [#1553](https://github.com/opendatateam/udata/pull/1553)
- Fix some search unicode issues [#1555](https://github.com/opendatateam/udata/pull/1555)
- Small fixes on OEmbed URL detection [#1556](https://github.com/opendatateam/udata/pull/1556)
- Use nb_hits instead of views to count downloads [#1560](https://github.com/opendatateam/udata/pull/1560)
- Prevent an XSS in TermFacet [#1561](https://github.com/opendatateam/udata/pull/1561)
- Fix breadcrumb bar layout on empty search result [#1562](https://github.com/opendatateam/udata/pull/1562)

## 1.3.4 (2018-03-28)

- Remove territory claim banner [#1521](https://github.com/opendatateam/udata/pull/1521)
- Expose an [OEmbed](https://oembed.com/) API endpoint using the new cards [#1525](https://github.com/opendatateam/udata/pull/1525)
- Small topic fixes [#1529](https://github.com/opendatateam/udata/pull/1529)
- Fixes the search result vertical cut off [#1530](https://github.com/opendatateam/udata/pull/1530)
- Prevent visually disabled pagination buttons from being clicked [#1539](https://github.com/opendatateam/udata/pull/1539)
- Fixes "sort organization by name" not working [#1537](https://github.com/opendatateam/udata/pull/1537)
- Non-admin users should not see the "publish as anyone" filter field on "publish as" screen [#1538](https://github.com/opendatateam/udata/pull/1538)

## 1.3.3 (2018-03-20)

- Fixes on upload: prevent double upload and bad chunks upload [#1516](https://github.com/opendatateam/udata/pull/1516)
- Ensure OAuth2 tokens can be saved without `refresh_token` [#1517](https://github.com/opendatateam/udata/pull/1517)

## 1.3.2 (2018-03-20)

- Support request-body credential in OAuth2 (Fix a regression introduced in 1.3.0) [#1511](https://github.com/opendatateam/udata/pull/1511)

## 1.3.1 (2018-03-15)

- Fix some geozones/geoids bugs [#1505](https://github.com/opendatateam/udata/pull/1505)
- Fix oauth scopes serialization in authorization template [#1506](https://github.com/opendatateam/udata/pull/1506)
- Prevent error on site ressources metric [#1507](https://github.com/opendatateam/udata/pull/1507)
- Fix some routing errors [#1508](https://github.com/opendatateam/udata/pull/1508)
- Mongo connection is now lazy by default, preventing non fork-safe usage in celery as well as preventing commands not using the database to hit it [#1509](https://github.com/opendatateam/udata/pull/1509)
- Fix udata version not exposed on Sentry [#1510](https://github.com/opendatateam/udata/pull/1510)

## 1.3.0 (2018-03-13)

### Breaking changes

- Switch to `flask-cli` and drop `flask-script`. Deprecated commands have been removed. [#1364](https://github.com/opendatateam/udata/pull/1364)
- Update card components to make them more consistent [#1383](https://github.com/opendatateam/udata/pull/1383) [#1460](https://github.com/opendatateam/udata/pull/1460)
- udata is now protocol (`http`/`https`) agnostic. This is now fully the reverse-proxy responsibility (please ensure that you are using SSL only in production for security purpose). [#1463](https://github.com/opendatateam/udata/pull/1463)
- Added more entrypoints and document them. There is no more automatically enabled plugin by installation. Plugins can now properly contribute translations. [#1431](https://github.com/opendatateam/udata/pull/1431)

### New features

- Soft breaks in markdown is rendered as line return as allowed by the [commonmark specifications](http://spec.commonmark.org/0.28/#soft-line-breaks), client-side rendering follows the same security rules [#1432](https://github.com/opendatateam/udata/pull/1432)
- Switch from OAuthlib/Flask-OUAhtlib to Authlib and support all grants type as well as token revocation [#1434](https://github.com/opendatateam/udata/pull/1434)
- Chunked upload support (big files support) [#1468](https://github.com/opendatateam/udata/pull/1468)
- Improve tasks/jobs queues routing [#1487](https://github.com/opendatateam/udata/pull/1487)
- Add the `udata schedule|unschedule|scheduled` commands [#1497](https://github.com/opendatateam/udata/pull/1497)

### Bug fixes and minor changes

- Added Geopackage as default allowed file formats [#1425](https://github.com/opendatateam/udata/pull/1425)
- Fix completion/suggestion unicode handling [#1452](https://github.com/opendatateam/udata/pull/1452)
- Added a link to change password into the admin [#1462](https://github.com/opendatateam/udata/pull/1462)
- Fix organization widget (embed) [#1474](https://github.com/opendatateam/udata/pull/1474)
- High priority for sendmail tasks [#1484](https://github.com/opendatateam/udata/pull/1484)
- Add security.send_confirmation template [#1475](https://github.com/opendatateam/udata/pull/1475)

### Internals

- Switch to pytest as testing tool and expose a `udata` pytest plugin [#1400](https://github.com/opendatateam/udata/pull/1400)


## 1.2.11 (2018-02-05)

- Translate Flask-Security email subjects [#1413](https://github.com/opendatateam/udata/pull/1413)
- Fix organization admin pagination [#1372](https://github.com/opendatateam/udata/issues/1372)
- Fix missing spinners on loading datatables [#1401](https://github.com/opendatateam/udata/pull/1401)
- Fixes on the search facets [#1410](https://github.com/opendatateam/udata/pull/1410)

## 1.2.10 (2018-01-24)

- Markdown rendering is now the same between the back and the frontend. [#604](https://github.com/opendatateam/udata/issues/604)
- Make the dataset page reuses section and cards themable. [#1378](https://github.com/opendatateam/udata/pull/1378)
- `ValueError` is not hidden anymore by the Bad Request error page, it is logged. [#1382](https://github.com/opendatateam/udata/pull/1382)
- Spatial encoding fixes: prevent breaking unicode errors. [#1381](https://github.com/opendatateam/udata/pull/1381)
- Ensure the multiple term search uses a `AND` operator [#1384](https://github.com/opendatateam/udata/pull/1384)
- Facets encoding fixes: ensure lazy strings are propery encoded. [#1388](https://github.com/opendatateam/udata/pull/1388)
- Markdown content is now easily themable (namespaced into a `markdown` class) [#1389](https://github.com/opendatateam/udata/pull/1389)
- Fix discussions and community resources alignment on datasets and reuses pages [#1390](https://github.com/opendatateam/udata/pull/1390)
- Fix discussions style on default theme [#1393](https://github.com/opendatateam/udata/pull/1393)
- Ensure empty harvest jobs properly end [#1395](https://github.com/opendatateam/udata/pull/1395)

## 1.2.9 (2018-01-17)

- Add extras field in discussions [#1360](https://github.com/opendatateam/udata/pull/1360)
- Fix datepicker [#1370](https://github.com/opendatateam/udata/pull/1370)
- Fix error on forbidden scheme in `is_url` harvest filter [#1376](https://github.com/opendatateam/udata/pull/1376)
- Fix an error on rendering present territory date [#1377](https://github.com/opendatateam/udata/pull/1377)

## 1.2.8 (2018-01-10)

- Fix html2text dependency version [#1362](https://github.com/opendatateam/udata/pull/1362)

## 1.2.7 (2018-01-10)

- Bump chartjs version to 2.x [#1352](https://github.com/opendatateam/udata/pull/1352)
- Sanitize mdstrip [#1351](https://github.com/opendatateam/udata/pull/1351)

## 1.2.6 (2018-01-04)

- Fix wrongly timed notification on dataset creation with misformed tags [#1332](https://github.com/opendatateam/udata/pull/1332)
- Fix topic creation [#1333](https://github.com/opendatateam/udata/pull/1333)
- Add a `udata worker status` command to list pending tasks.[breaking] The `udata worker` command is replaced by `udata worker start`. [#1324](https://github.com/opendatateam/udata/pull/1324)
- Prevent crawlers from indexing spammy datasets, reuses and organizations [#1334](https://github.com/opendatateam/udata/pull/1334) [#1335](https://github.com/opendatateam/udata/pull/1335)
- Ensure Swagger.js properly set jQuery.ajax contentType parameter (and so data is properly serialized) [#1126](https://github.com/opendatateam/udata/issues/1126)
- Allows theme to easily access the `owner_avatar_url` template filter [#1336](https://github.com/opendatateam/udata/pull/1336)

## 1.2.5 (2017-12-14)

- Fix misused hand cursor over the spatial coverage map in dataset admin [#1296](https://github.com/opendatateam/udata/pull/1296)
- Fix broken post edit page [#1295](https://github.com/opendatateam/udata/pull/1295)
- Display date of comments in dataset discussions [#1283](https://github.com/opendatateam/udata/pull/1283)
- Prevent `reindex` command from failing on a specific object and log error instead. [#1293](https://github.com/opendatateam/udata/pull/1293)
- Position the community resource link icon correctly [#1298](https://github.com/opendatateam/udata/pull/1298)
- Add a sort option to query of list of posts in API [#1301](https://github.com/opendatateam/udata/pull/1301)
- Import dropdown behavior from `udata-gouvfr` and fix hidden submenus on mobile [#1297](https://github.com/opendatateam/udata/pull/1297)
- show message for emtpy dataset search [#1044](https://github.com/opendatateam/udata/pull/1284)

## 1.2.4 (2017-12-06)

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
- CKAN and OpenDataSoft backends are now optional separate udata extensions [#1213](https://github.com/opendatateam/udata/pull/1213)
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
  [Flask-Security-Fork](https://pypi.org/project/Flask-Security-Fork)
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
- Ensure theme assets cache is versioned (and flushed when necessary)
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
See [Deprecation Policy](https://udata.readthedocs.io/en/stable/versioning/#deprecation-policy).

* Theses frequencies are deprecated for their Dublin Core counter part:
    * `fortnighly` ⇨ `biweekly`
    * `biannual` ⇨ `semiannual`
    * `realtime` ⇨ `continuous`


## 0.9.0 (2017-01-10)

- First published version
