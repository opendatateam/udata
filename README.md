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
- [Theme development](#theme-development)
  - [🚀 Getting started](#-getting-started)
    - [🐍 Python development](#-python-development)
      - [🧱 Installing the python dependencies](#-installing-the-python-dependencies)
      - [🚩 Starting the python development server](#-starting-the-python-development-server)
    - [☕ Javascript development](#-javascript-development)
      - [🏗 Installing the javascript dependencies](#-installing-the-javascript-dependencies)
      - [💪 Starting the javascript development server](#-starting-the-javascript-development-server)
    - [👀 Other dev commands](#-other-dev-commands)
  - [🏰 General architecture](#-general-architecture)
    - [🚜 Jinja2 templates](#-jinja2-templates)
    - [🚲 Javascript](#-javascript)
    - [🖼️ Style](#️-style)
  - [🛠️ Build tools](#️-build-tools)
  - [🏭 Javascript architecture](#-javascript-architecture)
    - [🏔️ Vue mounting](#️-vue-mounting)
    - [👩‍🔬 Tests](#-tests)
- [📖 Read more](#-read-more)

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

## Theme development

The front-end theme for the public facing website, is split into two parts :
- The [Jinja](https://jinja.palletsprojects.com/en/2.11.x/) templates are located inside `udata_front/theme/gouvfr/templates`.
- The [Less](https://lesscss.org/), [Vue](https://vuejs.org) & other sourcefiles for the front-end are located in `theme`.

### 🚀 Getting started

Before you start your developper journey, you have to setup your python and/or javascript development tools.

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

Modify your local `udata.cfg` configuration file as following:

```python
PLUGINS = ['front']
THEME = 'gouvfr'
```

#### 🐍 Python development

##### 🧱 Installing the python dependencies

Prepare a [udata development environment][udata-develop].

Note that we're using [pip-tools][udata-deps] on this repository too.

The following steps use the same Python virtual environment as `udata`.

Install `udata-front` in development mode:

```shell
cd udata-front
pre-commit install
pip install -e . -r requirements/test.pip -r requirements/develop.pip
```

> NB: the `udata.(in|pip)` files are used by the CI to stay in sync with `udata` requirements. You shouldn't need to tinker with them on your local environment, but they might be updated by the CI when you make a Pull Request.

##### 🚩 Starting the python development server


Simply run the udata project with udata-front loaded as a plugin:
```shell
cd udata
inv serve
```

#### ☕ Javascript development

##### 🏗 Installing the javascript dependencies

First, you need to use [Node](https://nodejs.org/) (version 14+) on your platform. You should consider [installing NVM](https://github.com/creationix/nvm#installation) which uses the existing .nvmrc.
```shell
cd udata-front

nvm install
nvm use

npm install
```

And voilà ! ✨

##### 💪 Starting the javascript development server

Simply run this command in the project directory :

```shell
npm start
```

This will start a development server that will listen to changes and automatically rebuild the project when needed.
Note that a webserver is started by Parcel (default port is `1234`), however we will not be using it as our CSS and JS files will be served by Jinja instead. More on that later.

#### 👀 Other dev commands

Finally, we have a bunch of commands to make your life a tad easier.

You can execute `udata-front` specific tasks from the `udata-front` directory with `invoke`. You can list available development commands with:

```shell
inv -l
```
Example commands:
- `i18n`: Extract translatable strings
- `i18nc`: Compile translations
- `qa`: Run a quality report
- `test`: Run tests suite

Additionally, you can run javascript-related commands through `npm run`.

- `build`: Builds the final CSS/JS files and the UI-Kit Documentation. You should probably use this one in production.
- `build:app`: Builds the final CSS/JS files without the UI-Kit
- `build:stylemark`: Builds the UI-Kit files and also the CSS/JS files but unminifed (do not use those static files in production)
- `i18n:report`: Generates a report of the i18n missing and unused keys
- `i18n:extract`: Same as above, but also automatically adds missing keys to translation files
- `clean`: Cleans Parcel cache. Use this if you stumble upon weird bugs to start anew.
- `start`: Get to coding with live reload and things. Same as `npm run dev`
- `test`: Runs the Cypress tests. More on that in the [Tests section](#-tests) of this README.

### 🏰 General architecture

#### 🚜 Jinja2 templates

Because [udata][] is written in Python, its templating engine is Jinja 2.
This means that the HTML received by clients is built at runtime, for each request, using templates with `{% block %}` tags and includes.

Those template are responsible for building the pages using layouts and blocks. Here are a few to get started (in `udata_front/theme/gouvfr/templates`), from less specific to more specific :

- `raw.html` : contains the general html structure exposing a `body` block where we can write our page's body. This template is also responsible for including the CSS and JS files.
- `base.html` : contains some extra html structure exposing a `content` block for our page's content, and wraps it around the header and footer.
- `header.html` and `footer.html` : standard header and footer block that will appear on each page
- `home.html`: the home page template (duh)

#### 🚲 Javascript

In order to add some interactivity to the project, we are using [Vue 3](https://v3.vuejs.org/api/) and some good old VanillaJS.
The JS assets are compiled in a single `index.js` file that includes everything for every page. If the bundle size starts to grow a little bit too much, you might need to think about splitting it into separate files for each page.

#### 🖼️ Style

We are using the [DSFR](https://github.com/GouvernementFR/dsfr) to build our front-end components.

In addition we have a nice litle set of CSS Utilities to quickly build custom components, inspired by bootstrap, most of its documentation
lives in the css located in `theme/less/` and is built using [Stylemark](https://github.com/mpetrovich/stylemark), you can read the live documentation in `udata_front/theme/stylemark/` after building it using `npm run build-stylemark`.

You can access the UI-kit documentation by visiting the following route : `/_stylemark/index.html`

Whenever a components needs some special styling, you can find their corresponding definitions inside `theme/less/specific/<component>`,
it's best if we can avoid having too much specific styling, but sometimes you just really need it.

### 🛠️ Build tools

This project uses [Parcel 2](https://github.com/parcel-bundler/parcel) to build and transform our source files into nice bundles for browsers.
Its config can be found in the `.parcelrc` file, as well as the `package.json` entries.

Parcel does multiple custom things in this project :

- Transform the `.js` files into modern Javascript for browsers
- Transform the `less` files into modern CSS using `PostCSS`
- Bundle the `svg` used in the JS files
- Copy the static assets when they change (config is in the `package.json`'s `staticFiles` key)
- Build the Stylemark (UI-kit) documentation on file change

### 🏭 Javascript architecture

#### 🏔️ Vue mounting

We are using the full build of VueJS that includes the compiler in order to compile templates directly in the browser.

There is a single VueJS app (in `index.js`) that contains every component and plugins.
However, this app is mounted multiple times, on each DOM node containing a `vuejs` class.

This allows us to mount the app only where it's needed, because each subsequent mount is more DOM to compile and thus has an impact on performance. Moreover, mounting to the smallest possible HTML allows us to prevent accidental XSS vulnerability by forbidding users to compile their content with the Vue engine.

In order to allow inter-component communication, a global event bus is available in the global app, under the `$bus` variable.
You can emit events by using `$bus.emit('event')` and components can listen to events by using `$bus.on('event')`.

#### 👩‍🔬 Tests

Tests are run in a headless browser using [Cypress](https://github.com/cypress-io/cypress). Test definitions are located in the `cypress/integration` directory.

Writing tests is very easy thanks to its syntax :

```js
  it("Displays the page title", () => {
    cy.get("h1").should("be.visible");
  });
```

Then, tests can be run using the following command :

```shell
npm run test
```

Cypress also comes with [cypress-axe](https://github.com/component-driven/cypress-axe) to allow for accessibility automated testing.

## 📖 Read more

[udata]: https://github.com/opendatateam/udata
[udata-doc]: http://udata.readthedocs.io/en/stable/
[udata-develop]: http://udata.readthedocs.io/en/stable/development-environment/
[udata-deps]: https://udata.readthedocs.io/en/stable/development-environment/#dependency-management
