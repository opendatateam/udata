<p align="center">
    <img src="https://user-images.githubusercontent.com/60264344/134811326-27109632-f653-4025-9786-482824635994.png">  
</p>
<p align="center">
    <i>⚙️ Udata customizations for data.gouv.fr made by Etalab ⚙️</i>
    <br>
    <br>
    <img src="https://img.shields.io/github/contributors/etalab/udata-front">
    <img src="https://img.shields.io/github/license/etalab/udata-front">
    <img src="https://img.shields.io/github/commit-activity/m/etalab/udata-front">
</p>

- [Notes on this repo](#notes-on-this-repo)
- [Compatibility](#compatibility)
- [Installation](#installation)
- [Development](#development)
- [Theme](#theme)
  - [TODO](#todo)

## Notes on this repo

This is a new version of [udata-gouvfr](https://github.com/etalab/udata-gouvfr)
This is a [udata][] extension, you should read the [udata documentation][udata-doc] first.

## Compatibility

**udata-front** requires Python 3.7+ and [udata][].


## Installation

Install [udata][].

Remain in the same Python virtual environment
and install **udata-front**:

```shell
pip install udata-front
```

Create a local configuration file `udata.cfg` in your **udata** directory
(or where your UDATA_SETTINGS point out) or modify an existing one as following:

```python
PLUGINS = ['front']
THEME = 'gouvfr'
```

## Development

Prepare a [udata development environment][udata-develop].

Note that we're using [pip-tools][udata-deps] on this repository too.

It is recommended to have a workspace with the following layout:

```shell
$WORKSPACE
├── fs
├── udata
│   ├── ...
│   └── setup.py
├── udata-front
│   ├── ...
│   └── setup.py
└── udata.cfg
```

The following steps use the same Python virtual environment
and the same version of npm (for JS) as `udata`.

Clone the `udata-front` repository into your workspace
and install it in development mode:

```shell
git clone https://github.com/etalab/udata-front.git
cd udata-front
pre-commit install
pip install -e . -r requirements/test.pip -r requirements/develop.pip
```

> NB: the `udata.(in|pip)` files are used by the CI to stay in sync with `udata` requirements. You shouldn't need to tinker with them on your local environment, but they might be updated by the CI when you make a Pull Request.

Modify your local `udata.cfg` configuration file as following:

```python
PLUGINS = ['front']
THEME = 'gouvfr'
```

You can execute `udata-front` specific tasks from the `udata-front` directory.

**ex:** Build the assets:

```shell
cd udata-front
npm install
inv assets-build
```

You can list available development commands with:

```shell
inv -l
```


## Theme

The front-end theme for the public facing website, is split into two parts :
- The [Jinja](https://jinja.palletsprojects.com/en/2.11.x/) templates are located inside `udata_front/theme/templates`.
- The [Less](http://lesscss.org/) & other sourcefiles for the are located in `theme`.

In addition we have a nice litle set of CSS Utilities to quickly build front end components, inspired by bootstrap, most of its documentation
lives in the css located in `theme/less/` and is built using [Stylemark](https://github.com/mpetrovich/stylemark), you can read the live documentation
in `udata_front/theme/stylemark/` after building it using `npm run build-stylemark`.

When building pages, here are a few templates to look out for in `udata_front/theme/gouvfr/templates` :
- `home.html` : well, duh.
- `header.html` and `footer.html` : same idea.
- `raw.html` : contains the general html structure exposing a `body` block where we can write our page's body.
- `base.html` : contains some extra html structure exposing a `content` block for our page's content.
- `subnav-large.html`, `publish-action-modal.html` and `carousel.html` : **TODO**

Here are our reusable components :
- `dataset` : datasets listings used in many pages.
- `reuse` : cards for displaying dataset reused in the real world.
- `participez` : is the large blue callout seen on multiple pages.
- `macros` : **TODO**
- `svg` : contains SVG assets to be included in our pages.

### TODO
Front docs todo :
- Parcel 2 architecture
  - Static copy
  - Stylemark build
  - VueJS compiler mode
- VanillaJS IIFE architecture
- Vue 3 architecture
  - Modals
  - I18n
  - Config plugin
  - Components
Back docs todo :
- CSS/JS file inclusion
- Static route for UI-Kit

Whenever a components needs some special styling, you can find their corresponding definitions inside `theme/less/specific/<component>`,
it's best if we can avoid having too much specific styling, but sometimes you just really need it.

Finally, we have a bunch of commands to make your life a tad easier, that you can run through `npm run`.
- `build`: Builds the final CSS/JS files and the UI-Kit Documentation. You should probably use this one.
- `build:app`: Builds the final CSS/JS files without the UI-Kit
- `build:stylemark`: Builds the UI-Kit files and also the CSS/JS files but unminifed (do not use those static files in production)
- `i18n:report`: Generates a report of the i18n missing and unused keys
- `i18n:extract`: Same as above, but also automatically adds missing keys to translation files
- `clean`: Cleans Parcel cache. Use this if you stumble upon weird bugs to start anew.
- `start`: Get to coding with live reload and things

[udata]: https://github.com/opendatateam/udata
[udata-doc]: http://udata.readthedocs.io/en/stable/
[udata-develop]: http://udata.readthedocs.io/en/stable/development-environment/
[udata-deps]: https://udata.readthedocs.io/en/stable/development-environment/#dependency-management
