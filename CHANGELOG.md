# Changelog

## Current (in progress)

- :warning: **breaking change**: Package renamming and new repository [#1](https://github.com/etalab/udata-front/pull/1):
  - udata-gouvfr is now udata-front

## 3.1.0 (2021-08-31)

- Add About in header [#623](https://github.com/etalab/udata-gouvfr/pull/623)
- Add link to profile in admin for sysadmin [#624](https://github.com/etalab/udata-gouvfr/pull/624)
- Remove 'Sort by' button on organization pages [#632](https://github.com/etalab/udata-gouvfr/pull/632)
- :warning: Use pip-tools for dependency management:
  - [#626](https://github.com/etalab/udata-gouvfr/pull/626)
  - [#631](https://github.com/etalab/udata-gouvfr/pull/631)
  - Documentation for install [here](https://github.com/etalab/udata-gouvfr#development)

## 3.0.7 (2021-08-17)

- Update crowdin translations [#622](https://github.com/etalab/udata-gouvfr/pull/622)

## 3.0.6 (2021-08-16)

- Update homepage wording [#617](https://github.com/etalab/udata-gouvfr/pull/617)
- Change banner trigger for geo.data.gouv.fr [#618](https://github.com/etalab/udata-gouvfr/pull/618)
- Show private datasets and reuses on organization page [#619](https://github.com/etalab/udata-gouvfr/pull/619)
- Make frontend banner configurable and remove newsletter banner settings [#621](https://github.com/etalab/udata-gouvfr/pull/621)

## 3.0.5 (2021-08-12)

- Add a banner on geo.data.gouv.fr's datasets [#607](https://github.com/etalab/udata-gouvfr/pull/607)

## 3.0.4 (2021-08-12)

- Replace mdstrip filter with markdown in resources descriptions [#606](https://github.com/etalab/udata-gouvfr/pull/606)
- Fix numerous responsive issues and prevent VueJS from crashing the page on compilation error [#605](https://github.com/etalab/udata-gouvfr/pull/605)
- Replace old COVID-19 inventory button with the new one for santé [#608](https://github.com/etalab/udata-gouvfr/pull/608)
- Add SPD datasets to home page [#609](https://github.com/etalab/udata-gouvfr/pull/609)
- Remove duplicate Participate block on dataset page [#611](https://github.com/etalab/udata-gouvfr/pull/611)
- Add redirect to dataset on submit for suggest search [#612](https://github.com/etalab/udata-gouvfr/pull/612)

## 3.0.3 (2021-07-30)

- Add new translations [#603](https://github.com/etalab/udata-gouvfr/pull/603)
- Add vue sentry logging on gouvfr [#594](https://github.com/etalab/udata-gouvfr/pull/594)
- Add all featured topics button on homepage [#597](https://github.com/etalab/udata-gouvfr/pull/597)
- Resources descriptions are no longer truncated [#596](https://github.com/etalab/udata-gouvfr/pull/596)
- Fix URL for dataset search params [#595](https://github.com/etalab/udata-gouvfr/pull/595)

## 3.0.2 (2021-07-19)

- Add organization search [#593](https://github.com/etalab/udata-gouvfr/pull/593)
- Fix reuses filters issue [#592](https://github.com/etalab/udata-gouvfr/pull/592)
- Remove suggest on mobile [#590](https://github.com/etalab/udata-gouvfr/pull/590)
- Added homepage "venti" button for the new inventory [#591](https://github.com/etalab/udata-gouvfr/pull/591)

## 3.0.1 (2021-07-09)

- Fix datasets search pagination reset [#588](https://github.com/etalab/udata-gouvfr/pull/588)
- Replace link to /search route by /datasets [#587](https://github.com/etalab/udata-gouvfr/pull/587)
- Removed useless templates, views and tests after v3 [#557](https://github.com/etalab/udata-gouvfr/pull/557)
- Fix datasets search pagination [#585](https://github.com/etalab/udata-gouvfr/pull/585)

## 3.0.0 (2021-07-07)

- :warning: **breaking change**: most of the theme/templates logic has been moved from https://github.com/opendatateam/udata to this repo. `udata` no longer contains a default theme. In the 3.x series, we hope it will be usable as a "headless" open data platform, but for now you probably need to plug your own theme or use udata-gouvfr. [More info about this change here](https://github.com/opendatateam/udata/blob/master/docs/roadmap/udata-3.md#the-road-to-udata3). [#492](https://github.com/etalab/udata-gouvfr/pull/492)

## 2.6.2 (2021-05-25)

- New translations [#535](https://github.com/etalab/udata-gouvfr/pull/535)

## 2.6.1 (2021-05-25)

- Add new translations [#518](https://github.com/etalab/udata-gouvfr/pull/518)

## 2.6.0 (2021-05-25)

- [maaf] fix encoding issue [#531](https://github.com/etalab/udata-gouvfr/pull/531)
- Add link to support page [#532](https://github.com/etalab/udata-gouvfr/pull/532)
- UX enhancement [#525](https://github.com/etalab/udata-gouvfr/pull/525):
  - Removed hero's background image.
  - Removed home page's carrousel.
  - Changed homepage's layout. Datasets are now on top followed by reuses.
  - Renamed "Profile" to "Public profile"

## 2.5.5 (2021-04-02)

- Thanks for all the fish [#529](https://github.com/etalab/udata-gouvfr/pull/529)

## 2.5.4 (2021-03-31)

- 🦀

## 2.5.3 (2021-03-23)

- Add venv activation in CircleCI's publish step [#526](https://github.com/etalab/udata-gouvfr/pull/526)

## 2.5.2 (2021-03-22)

- Keep tracking to strictly necessary [#517](https://github.com/etalab/udata-gouvfr/pull/517)
- Changed the title of the elections inventory page [#520](https://github.com/etalab/udata-gouvfr/pull/520)

## 2.5.1 (2021-01-26)

- New Crowdin translations [#511](https://github.com/etalab/udata-gouvfr/pull/511)

## 2.5.0 (2021-01-25)

- Add Inventory cards on homepage [#514](https://github.com/etalab/udata-gouvfr/pull/514)
- Add documentation's dropdown menu with links to technical documentation and open data guides [#516](https://github.com/etalab/udata-gouvfr/pull/516)

## 2.3.0 (2020-11-30)

- Read Only Mode modifications on theme [#509](https://github.com/etalab/udata-gouvfr/pull/509):
  - Will display a warning banner on the frontend view.
  - Hides the contribute's home's modal.
  - Hides the Reuse's creation card and community resource's creation card on dataset view.
- Newsletter's subscription banner [#512](https://github.com/etalab/udata-gouvfr/pull/512):
  - Override alert section in posts list template to display newsletter's subscription banner.
  - Add settings `POST_BANNER_ACTIVATED` to toggle banner's activation.
  - Add settings `POST_BANNER_LINK` and `POST_BANNER_MESSAGE` to configure subscription's link and message.

## 2.2.3 (2020-11-09)

- Add news link to posts list [#504](https://github.com/etalab/udata-gouvfr/pull/504)

## 2.2.2 (2020-10-16)

- Pinned udata version to fix transitive requests dependencies [#500](https://github.com/etalab/udata-gouvfr/pull/500)

## 2.2.1 (2020-10-16)

- Banner is now generic and configurable [#499](https://github.com/etalab/udata-gouvfr/pull/499)
- Fix links in static pages

## 2.2.0 (2020-08-25)

- Show api.gouv.fr APIs on dataset page [#493](https://github.com/etalab/udata-gouvfr/pull/493)

## 2.1.5 (2020-08-05)

- Mise à jour de l'URL de Geo SIRENE [#489](https://github.com/etalab/udata-gouvfr/pull/489)
- Add footer link to pages summary and page cache [#488](https://github.com/etalab/udata-gouvfr/pull/488)

## 2.1.4 (2020-06-29)

- Add static /pages/* from md in github repo [#483](https://github.com/etalab/udata-gouvfr/pull/483)

## 2.1.3 (2020-06-16)

- Fix packaging

## 2.1.1 (2020-06-11)

- Adding banner with setting inherited from udata's settings [#480](https://github.com/etalab/udata-gouvfr/pull/480)

## 2.1.0 (2020-05-13)

- Remove public services metrics [#472](https://github.com/etalab/udata-gouvfr/pull/472)

## 2.0.2 (2020-04-22)

- Ajout du _flag_ "recherche" pour activer le _widget_ d'experimentation de recherche [#466](https://github.com/etalab/udata-gouvfr/pull/466/commits/9c42b5aa8e6e0e37f471a32182196b989bc41a68)

## 2.0.1 (2020-03-24)

- Add covid-19 badge for datasets and reuses [#473](https://github.com/etalab/udata-gouvfr/pull/473)

## 2.0.0 (2020-03-11)

- Migrate to python3 🐍 [#453](https://github.com/etalab/udata-gouvfr/pull/453)

## 1.6.13 (2019-12-13)

- Ajout de l'identifiant SPDX pour la licence Ouverte 2.0 [#437](https://github.com/etalab/udata-gouvfr/pull/437)
- Lien vers la doc d'API externe dans le footer [#438](https://github.com/etalab/udata-gouvfr/pull/438)
- Mise à jour de l'URL de Geo SIRENE [#446](https://github.com/etalab/udata-gouvfr/pull/446)

## 1.6.12 (2019-09-11)

- Nouvelle section contact dans le pied de page [#428](https://github.com/etalab/udata-gouvfr/pull/428)
- Suppression du konami code [#429](https://github.com/etalab/udata-gouvfr/pull/429)

## 1.6.11 (2019-07-11)

- New social logo (`og:image`) [#419](https://github.com/etalab/udata-gouvfr/pull/419)

## 1.6.10 (2019-06-26)

- Data catalog: id as ref instead of slug [#415](https://github.com/etalab/udata-gouvfr/pull/415)
- Add cache for topic display page [#414](https://github.com/etalab/udata-gouvfr/pull/414)
- Fix card size on dataset page [#418](https://github.com/etalab/udata-gouvfr/pull/418)

## 1.6.9 (2019-06-07)

- Switch removal of related tags in a topic page to a proper `related` jinja tag [#408](https://github.com/etalab/udata-gouvfr/pull/408)
- Add the homologation of IGN licenses [#412](https://github.com/etalab/udata-gouvfr/pull/412)

## 1.6.8 (2019-05-29)

- Minor edits on SPD [#406](https://github.com/etalab/udata-gouvfr/pull/406)
- Change certification visual location in cards [#407](https://github.com/etalab/udata-gouvfr/pull/407)

## 1.6.7 (2019-05-23)

- Set org logo to max width [#403](https://github.com/etalab/udata-gouvfr/pull/403)
- Add data catalog link to footer [#404](https://github.com/etalab/udata-gouvfr/pull/404)

## 1.6.6 (2019-05-20)

- Remove clutter from search bar [#400](https://github.com/etalab/udata-gouvfr/pull/400)
- Add the homologation of INPI licenses [#402](https://github.com/etalab/udata-gouvfr/pull/402)

## 1.6.5 (2019-05-10)

- Home blog post extraction improvements. Supports both Atom and RSS 2.0, more image tag formats, `media:thumbnail` and enclosures. [#385](https://github.com/etalab/udata-gouvfr/pull/385)
- Pin version of `requests` [#397](https://github.com/etalab/udata-gouvfr/pull/397)
- Improve header menu legibility [#388](https://github.com/etalab/udata-gouvfr/pull/388)

## 1.6.4 (2019-03-27)

- Updates topic entry page [#382](https://github.com/etalab/udata-gouvfr/pull/382)

## 1.6.3 (2019-03-06)

- Remove "compte des collectivités" from territories [#376](https://github.com/etalab/udata-gouvfr/pull/376)
- Push discussion under reuses and community resources [378](https://github.com/etalab/udata-gouvfr/pull/378)

## 1.6.2 (2018-11-17)

- Konami code 🥚 [#362](https://github.com/etalab/udata-gouvfr/pull/362) NB: this is not a release worth installing except on [data.gouv.fr](https://data.gouv.fr).

## 1.6.1 (2018-11-05)

- Add a BAL badge [#347](https://github.com/etalab/udata-gouvfr/pull/347)
- Remove TOS opt-in subtext [#349](https://github.com/etalab/udata-gouvfr/pull/349)

## 1.6.0 (2018-10-02)

- Make use of assets manifest for long term caching [#328](https://github.com/etalab/udata-gouvfr/pull/328)
- Discussion add card style coherence [#339](https://github.com/etalab/udata-gouvfr/pull/339)
- Remove a duplicate rule on `.dataset-container h3`

## 1.4.4 (2018-08-27)

- Fix the multisearch labels position [#330](https://github.com/etalab/udata-gouvfr/pull/330)

## 1.4.3 (2018-08-08)

- Fix the navbar toggle button position 🎊 [#327](https://github.com/etalab/udata-gouvfr/pull/327)

## 1.4.2 (2018-07-30)

- Add a reference on the page about SPD [#318](https://github.com/etalab/udata-gouvfr/pull/318)

## 1.4.1 (2018-06-06)

- Fix packaging

## 1.4.0 (2018-06-06)

- Typed resources related styles [#265](https://github.com/etalab/udata-gouvfr/pull/265)
- Enforce a domain whitelist when resource.filetype is file (migration) [#292](https://github.com/etalab/udata-gouvfr/pull/292)
- Use new pypi.org links [#295](https://github.com/etalab/udata-gouvfr/pull/295)
- Ensure active users have a confirmed_at date (migration) [#298](https://github.com/etalab/udata-gouvfr/pull/298)
- Remove credits page [#306](https://github.com/etalab/udata-gouvfr/pull/306)
- Fix `modal-lg` width [#311](https://github.com/etalab/udata-gouvfr/pull/311)
- Add tracking and privacy page [#310](https://github.com/etalab/udata-gouvfr/pull/310)

## 1.3.2 (2018-03-28)

- Limit number of forum topics [#284](https://github.com/etalab/udata-gouvfr/pull/284)
- Use new OEmbed cards in datasets recommandations [#285](https://github.com/etalab/udata-gouvfr/pull/285)
- Fix the RSS popover not being clickable [#287](https://github.com/etalab/udata-gouvfr/pull/287)
- Drop the custom style for non-certified datasets [#288](https://github.com/etalab/udata-gouvfr/pull/288)

## 1.3.1 (2018-03-15)

- Fix some cards positionning

## 1.3.0 (2018-03-13)

- Make use of [udata pytest plugin](https://github.com/opendatateam/udata#1400) [#254](https://github.com/etalab/udata-gouvfr/pull/254)
- Expose new entrypoints. Plugins and theme translations are now splitted [#263](https://github.com/etalab/udata-gouvfr/pull/263)
- Align card components design [#252](https://github.com/etalab/udata-gouvfr/pull/252) [#272](https://github.com/etalab/udata-gouvfr/pull/272)
- Discourse timeout and response parse error catch [#267](https://github.com/etalab/udata-gouvfr/pull/267)
- Add tracking on home page call to action [#271](https://github.com/etalab/udata-gouvfr/pull/271)
- Add tracking on carousel elements [#268](https://github.com/etalab/udata-gouvfr/pull/268)
- Temporary carousel layout [#274](https://github.com/etalab/udata-gouvfr/pull/274)
- Add tracking of dataset recommendations [#277](https://github.com/etalab/udata-gouvfr/pull/277)

## 1.2.5 (2018-02-05)

- Small fixes on search facets related to [opendatateam/udata#1410](https://github.com/opendatateam/udata/pull/1410) [#255](https://github.com/etalab/udata-gouvfr/pull/255)

## 1.2.4 (2018-01-24)

- Licenses: Update SHOM attachment + fix BAN URL [#249](https://github.com/etalab/udata-gouvfr/pull/249)

## 1.2.3 (2018-01-17)

- Add the homologation of CC-BY-SA for SHOM [#244](https://github.com/etalab/udata-gouvfr/pull/244/files)
- Dataset recommendations [#243](https://github.com/etalab/udata-gouvfr/pull/243)
- Move some discussions style into `udata` core [#251](https://github.com/etalab/udata-gouvfr/pull/251)

## 1.2.2 (2017-12-14)

- Export CSS dropdown behavior to `udata` [#234](https://github.com/etalab/udata-gouvfr/pull/234)
- Remove internal FAQ and switch to [doc.data.gouv.fr](https://doc.data.gouv.fr) [#236](https://github.com/etalab/udata-gouvfr/issues/236)

## 1.2.1 (2017-12-06)

- Export community resource avatar style to udata [#233](https://github.com/etalab/udata-gouvfr/pull/233)
- Drop the `terms.html` template. Terms and conditions are now externalized and use the udata core template. (See [udata#1285](https://github.com/opendatateam/udata/pull/1285)) [#232](https://github.com/etalab/udata-gouvfr/pull/232)

## 1.2.0 (2017-10-20)

- Use new search blueprint from uData [#224](https://github.com/etalab/udata-gouvfr/pull/224)

## 1.1.2 (2017-09-04)

- Fixes some spacing issues on dataset and reuses page buttons
  [#209](https://github.com/etalab/udata-gouvfr/pull/209)
- Fix some wrong spatial coverages
  [#213](https://github.com/etalab/udata-gouvfr/pull/213)
- Fix translations collision on contact [#211](https://github.com/etalab/udata-gouvfr/pull/211) [#212](https://github.com/etalab/udata-gouvfr/pull/212)
- Updated some translations

## 1.1.1 (2017-07-31)

- Updated translations

## 1.1.0 (2017-07-05)

- Use the new entrypoint-based theme management
  [#164](https://github.com/etalab/udata-gouvfr/pull/164)
- Adjust the dataset reuses title overflow for proper display
  [#172](https://github.com/etalab/udata-gouvfr/pull/172)
- Drop glyphicons, remove some useless classes and upgrade to bootstrap 3.3.7
  [#177](https://github.com/etalab/udata-gouvfr/pull/177)
- Use the core publish action modal
  [#178](https://github.com/etalab/udata-gouvfr/pull/178)
- Fix the deuil header not being an SVG
  [#180](https://github.com/etalab/udata-gouvfr/pull/180)
- Integrating latest versions of GeoZones and GeoLogos for territories.
  Especially using history of towns, counties and regions from GeoHisto.
  [#499](https://github.com/opendatateam/udata/issues/499)
- Add the missing placeholders
  [#194](https://github.com/etalab/udata-gouvfr/pull/194)
- Use the `udata.harvesters` entrypoint
  [#195](https://github.com/etalab/udata-gouvfr/pull/195)
- Revamp actionnable tabs
  [#189](https://github.com/etalab/udata-gouvfr/pull/189)
- Remove `.btn-more` class
  [#191](https://github.com/etalab/udata-gouvfr/pull/191)

## 1.0.9 (2017-06-28)

- Nothing yet

## 1.0.8 (2017-06-21)

- Fixed a typo
  [#182](https://github.com/etalab/udata-gouvfr/pull/182)

## 1.0.7 (2017-06-20)

- Added a Licences page
  [#181](https://github.com/etalab/udata-gouvfr/pull/181)

## 1.0.6 (2017-04-18)

- Fixed numbering in system integrator FAQ (thanks to Bruno Cornec)
  [#174](https://github.com/etalab/udata-gouvfr/pull/174)
- Added a footer link to the SPD page
  [#176](https://github.com/etalab/udata-gouvfr/pull/176)

## 1.0.5 (2017-04-06)

- Added a missing translation
- Alphabetical ordering on SPD datasets

## 1.0.4 (2017-04-05)

- Introduce SPD page and badge

## 1.0.3 (2017-02-27)

- Translations update
- Switch `udata-js` link to `metaclic` [#161](https://github.com/etalab/udata-gouvfr/pull/161)

## 1.0.2 (2017-02-21)

- Optimize png images from theme [#159](https://github.com/etalab/udata-gouvfr/issues/159)
- Optimize png images sizes for territory placeholders [#788](https://github.com/opendatateam/udata/issues/788)

## 1.0.1 (2017-02-20)

- Ensure missing FAQ sections raises a 404 [#156](https://github.com/etalab/udata-gouvfr/issues/156)
- Provide deep PyPI versions links into the footer [#155](https://github.com/etalab/udata-gouvfr/pull/155)
- Provide proper cache versionning for theme assets [#155](https://github.com/etalab/udata-gouvfr/pull/155)

## 1.0.0 (2017-02-16)

- Remove some main menu entries (events, CADA, Etalab)
- Use a new SVG logo
- Apply changes from [uData 1.0.0](https://pypi.org/project/udata/1.0.0#changelog)

## 0.9.1 (2017-01-10)

- First published release
