# Using plugins

To use plugins, you first need to install it, ex:
```
pip install udata-ckan
```

Then you can modify your config file (`udata.cfg`) and add the plugin to the list:
```
PLUGINS = ['front', 'ckan', ...]
```

# Creating your own plugins

See [extending udata](extending.md) guide to create your own plugin.

# Known plugins

Here a list of known plugins for udata:

- [`udata-front`][udata-front], a plugin for a udata fronted
- [`udata-piwik`][udata-piwik], a plugin for integration between udata and [Piwik/Matomo][matomo]
- [`udata-metrics`][udata-metrics], a plugin that handles a connexion to an InfluxDB service for udata metrics (number of hits, downloads, etc.)
- [`udata-ckan`][udata-ckan], [CKAN][ckan] integration for udata
- [`udata-ods`][udata-ods], [OpenDataSoft][ods] integration for udata
- [`udata-dcat`][udata-dcat], [DCAT][dcat] integration for udata
- [`udata-recommendations`][udata-recommendations], a plugin to integrate a recommendation system
- [`udata-tabular-preview`][udata-tabular-preview], a plugin to preview tabular files (CSV, Excel, ...) using [csvapi][csvapi]
- [`udata-data-fair`][udata-data-fair], a plugin that use [DataFair][datafair] embeds to preview data
- [`udata-transport`][udata-transport], a plugin to bind datasets to their counterparts on [transport.data.gouv.fr][transport.data.gouv.fr]


!!! note
    Don't hesitate to submit a pull-request to add your udata plugin to this list.

[udata-front]: https://github.com/etalab/udata-front
[udata-piwik]: https://github.com/opendatateam/udata-piwik
[udata-metrics]: https://github.com/opendatateam/udata-metrics
[udata-ckan]: https://github.com/opendatateam/udata-ckan
[udata-ods]: https://github.com/opendatateam/udata-ods
[udata-dcat]: https://github.com/opendatateam/udata-dcat
[udata-recommendations]: https://github.com/opendatateam/udata-recommendations
[udata-tabular-preview]: https://github.com/opendatateam/udata-tabular-preview
[udata-data-fair]: https://github.com/koumoul-dev/udata-data-fair
[udata-transport]: https://github.com/opendatateam/udata-transport
[matomo]: https://matomo.org/
[ckan]: https://ckan.org/
[ods]: https://www.opendatasoft.com/
[dcat]: https://github.com/opendatateam/udata/blob/master/udata/harvest/backends/dcat.py
[csvapi]: https://github.com/opendatateam/csvapi
[datafair]: https://data-fair.github.io/3/
[transport.data.gouv.fr]: https://transport.data.gouv.fr/