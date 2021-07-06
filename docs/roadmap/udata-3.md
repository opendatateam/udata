# The Road to udata 3

### *What is udata?* 

[udata](https://github.com/opendatateam/udata) is the free software that provides the core features of [data.gouv.fr, the French government open data portal](https://www.data.gouv.fr/fr/). It has been developed in the open since 2013 and is freely reused and customized by a few countries (Luxembourg, Serbia, Portugal), some government agencies and at least one NGO.

That latest major breaking release, [udata 2](https://github.com/opendatateam/udata/blob/master/CHANGELOG.md#200-2020-03-11), focused mainly on the migration to python 3, right before the deadline of python 2 support being dropped. Since then, we shipped six minor releases and more patches.

### *Who’s behind udata?*
An [overwhelming majority of commits](https://github.com/opendatateam/udata/graphs/contributors) on udata have been made by members of [Etalab](https://www.etalab.gouv.fr), the French government agency responsible for data.gouv.fr. 

The technical team dedicated at Etalab responsible not only for development but also for operating the platform and handling user support has always been relatively small: between one and three people.

### *The burden of technical debt*

The software has been starting to show signs of heavy technical debt a few years ago, despite our best “rolling” refactoring efforts while working on the maintenance and new features.

This explains why we have been looking for ways to ease the burden of maintaining such a complex piece of software, while being able to work on innovative features and services with such a small team.

Some of those ways are not directly related to udata. A few years ago, we started to **implement new features through external services rather than add them directly in udata**. Those services are interfaced with udata/data.gouv.fr through a thin wrapper. A good example of this approach is [csvapi](https://github.com/etalab/csvapi) which provides a data preview feature to data.gouv.fr. This service lives independently from udata and is interfaced with it through a [small plugin](https://github.com/opendatateam/udata-tabular-preview). Nothing new here, this is fairly close to the Unix philosophy: have one tool do a job well and interface it with others. We found that this approach has let us iterate and experiment faster and we will probably keep applying it in the future.

Regarding udata directly, one of the heaviest burdens we face is to maintain two themes:
- One default minimalist theme shipped with udata, meant as a starting basis for other users of udata. We never use this theme directly but we still have to test and fix things on it before shipping,
- The “official” theme used by data.gouv.fr: [udata-gouvfr](https://github.com/etalab/udata-gouvfr), inherited from the default theme.

### *Graphical redesign as an opportunity to reduce technical debt*

In this context, we recently started a project of total graphical overhaul of data.gouv.fr. 

This was the perfect opportunity to reflect upon our choices regarding the legacy theme mechanism. **We concluded that with our limited resources, the minimalist default theme had to go**. We couldn’t possibly continue to maintain both versions with a complex inheritance mechanism while going through the process of rewriting data.gouv.fr’s theme completely. This already being quite a daunting task for us while continuing to operate the platform and shipping new features.

This also led us to reflect more profoundly upon “separation of concerns” in our product. As stated previously, we believe in interconnected services more than in a one-size-fits-all monolith. Once again, the graphical redesign and the decision to get rid of the legacy theme provided an opportunity to move toward that goal. **We can now separate the core logic (i.e., the open data catalog, user, discussions, reuses, APIs, etc.) from the presentation logic (i.e., the views) which will now live within the theme**. 

We believe this will ultimately lead to an easier way to maintain product, allowing use to iterate more rapidly on the API for example, without breaking the presentation logic. As a side note, we could have gone to the SPA way on top of our APIs for our new front end, but we chose not to, mainly for performance and SEO reasons.

### *What’s next?*

This is the road to udata 3. We don’t have a release date yet and there are a lot of corner cases yet to be handled. The 3.0 release will probably still have some entanglement between the core part and the theme part but we plan to iterate on that in the 3.x series. 

We hope this has given you at least an insight into the future of udata, which will keep powering data.gouv.fr for the foreseeable future. We’d also love to hear from you if you some insights as a udata user.
