# Creating a custom theme

The project as been developed from start with the goal to make it generic and reusable.
The theme engine is based on [Flask-Themes2][] so reading its documentation might help.

To create your custom theme, the easiest way is to start from the
[dedicated cookiecutter template][cookiecutter-template]:

```bash
pip install cookiecutter
cookiecutter gh:opendatateam/cookiecutter-udata-theme
```
This will create a new theme skeleton on which you can start hacking.

As udata is Bootstrap-based (only the style part),
the difficulty will depends on what you cant to do:

- customize some style and colors ⇨ very easy
- customize the layouts or how some part of udata is rendered ⇨ easy
- switch to another style framework ⇨ hard

## Project layout

A theme has the following layout.

```
├── my_theme
│   ├── static
│   │   ├── theme.css
│   │   ├── admin.css
│   │   └── img
│   │       ├── flags
│   │       └── placeholders
│   ├── templates
│   │   └── *.html
│   ├── translations
│   │   ├── xx/LC_MESSAGES
│   │   │   └── my-theme.po
│   │   └── my-theme.pot
│   ├── info.json
│   └── __init__.py
├── babel.cfg
├── CHANGELOG.md
├── MANIFEST.in
├── README.md
├── setup.cfg
└── setup.py
```

At the root level, you will have some basic python project files:

- a `README.md` presenting the theme and how to use it
- a `CHANGELOG.md` to let people know the last changes in your theme
- a `MANIFEST.in` which specify which files should be included in your theme package
- a `setup.py` exposing the package metadata (including the theme presence)
- a `setup.cfg` configuring translations commands
- a `babel.cfg` configuring translations extractor

In the package directory (`my_theme` in this example), you need to have two files:

- `info.json` exposing metadata required by the theme loader
- `__init__.py` which is required by a Python package. It can be empty or contains hooks.

There can also be three directories:

- `static` containing static assets (images, styles, extra scripts...)
- `templates` containing the overriden templates (optionnal).
- `translations` containing the overriden translated strings (optionnal).

!!! note
    This is a proposal layout for a standalone theme.
    As long as the theme package has the proper layout (`info.json`, `__init__.py`...),
    it can be wherever you want if you properly expose it in your `setup.py` file.

## `setup.py`

The `setup.py` is a classic python `setup.py` file.
The only requirement is that you properly expose the udata theme packaging
as `udata.themes` entrypoint:

```python
setup(
    '...'
    entry_points={
        'udata.themes': [
            'any-identifier = canonical.theme.package',
        ]
    },
    '...'
)
```

## `info.json`

The ``info.json`` looks like this:

```json
{
    "application": "udata",
    "identifier": "my-theme",
    "name": "My awesome theme",
    "author": "Me",
    "description": "An awesome theme for udata",
    "website": "http://awesome.opendata.tem",
    "license": "AGPL",
    "version": "0.1.0",
    "doctype": "html5"
}
```
The `application` and the `doctype` attributes needs to have specific values, respectively `udata` and `html5`.
The `identifier` attribute is important: this is the value you will be using in `udata.cfg` to use your theme
(the `THEME` parameter).
Any other attribute can have any value, this is only metadata.

## Static assets

The `static` should contain at least 2 files:

- `theme.css` which is loaded automatically on every page
- `admin.css` which is loaded automatically on on the admin page

Some images are required and used everywhere in the application:

- `img/flags` contains the language switcher flags in the form `{language code}.png` (ex. `en.png`).
- `img/placeholders` contains default images for:
    - users without avatar (`user.png`)
    - organizations without logo (`organization.png`)
    - reuses without image (`reuse.png`)
    - territory without logo or flag (`territory.png`)

Then you are free to add any static assets required by your theme.

## Overriding templates

You can override or extend any default Jinja template.
You only need to put the templates with the same name into the `templates` folder.

To extend a template and change some details, just extend the base template and override the block you want to change:

```html+jinja
{% extends "raw.html" %}

{% block raw_head %}
{{ super() }}
<link rel="shortcut icon" href="{{ theme_static('img/favicon.png') }}">
{% endblock %}
```
You can reference static assets from your theme with the `theme_static` global function.

!!! note
    Don't forget to call `{{ super() }}` to includes the original block.
    See the [Jinja documentation][] for advanced usage.

You can also rewrite entirely the template, but don't forget you need to have the proper blocks
for template inheritance and use the proper context variables.

## Hooks

Your theme can also customize some behavior by using hooks in your ``__init__.py``.
Currently there are 2 available hooks:

- `theme.menu()` to register a custom main menu
- `theme.context()` to add extra context variable to some views

You can also expose extras menus using the `udata.app.nav` extension.
They will be available in the template context under the `nav` object.

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata import theme
from udata.app import nav
from udata.i18n import lazy_gettext as _

# Expose a menu available globaly as `nav.my_menu`
my_menu = nav.Bar('my_menu', [
    nav.Item(_('Data'), 'datasets.list', items=[
        nav.Item(_('Datasets'), 'datasets.list'),
        nav.Item(_('Reuses'), 'reuses.list'),
        nav.Item(_('Organizations'), 'organizations.list'),
    ]),
    nav.Item(_('Dashboard'), 'site.dashboard'),
])

# Register it as default main menu
theme.menu(my_menu)

# Expose another menu available globaly as 'nav.my_network'
nav.Bar('my_network', [
    nav.Item(label, label, url=url) for label, url in [
        ('awesome.fr', 'http://www.awesome.fr'),
        ('somewhere.net', 'https://somewhere.net'),
    ]
])

# Add some context to the home view
@theme.context('home')
def home_context(context):
    context['something'] = 'some value'
    return context
```

!!! note
    You can see an example of advanced hooks usage in the [`gouvfr` theme][gouvfr-hooks].

## Translations

You can also (and optionnaly) add or override some translations in you theme.

If the `translations` directory is present and contains some gettext-based translations(`po/mo` files),
they will be loaded after all others and so they will override existing ones.

The cookiecutter template makes use of [Babel][] to extract string from your template
or compile them.

You can extract translations from your own templates using:

```bash
python setup.py extract_messages  # Extract messages in your pot file
```

Then you can either add new supported locale:

```bash
python setup.py init_catalog -l xx  # where XX is the locale you want to add. ex: fr
```

or update the existing ones:

```bash
python setup.py update_catalog
```

You can then translate the po file using the editor of your choice
(take a look at [Poedit][]).

When translation is done, you can compile translations catalogs using:

```bash
python setup.py compile_catalog  # Compile .mo files for each language
```

!!! warning
    Don't forget to compile and include translations in your theme distribution
    when you publish it.

## Publish and use

Once your theme is ready, you can publish it on [PyPI][] to share it to the world
(and notify us so we can be glad of your work).

To do so, simply execute the following command at the root of your theme project:

```bash
python setup.py bdist_wheel upload
```

Then it will be available on [PyPI][] and you can use it on your platform by installing it
and setting properly the ``THEME`` parameter in your `udata.cfg`.

# Known themes

Here a list of known themes for udata:

- [`default`][default-theme]: default theme packaged with udata (does nothing)
- [`gouvfr`][gouvfr-project] as part of the [`gouvfr` plugin][gouvfr-project].


!!! note
    Don't hesitate to submit a pull-request to add your theme to this list.

## Help

You can ask for help on the [udata gitter channel][gitter-chan].
Please report any difficulty you encounter with a dedicated [Github issue][github-new-issue].

[Flask-Themes2]: http://flask-themes2.readthedocs.io/en/latest/
[Jinja documentation]: jinja.pocoo.org/docs/
[github-new-issue]: https://github.com/opendatateam/udata/issues/new
[cookiecutter-template]: https://github.com/opendatateam/cookiecutter-udata-theme
[Babel]: http://babel.pocoo.org/
[PyPI]: https://pypi.python.org/
[gitter-chan]: https://gitter.im/opendatateam/udata
[gouvfr-hooks]: https://github.com/etalab/udata-gouvfr/blob/master/udata_gouvfr/theme/__init__.py
[Poedit]: https://poedit.net/
[gouvfr-project]: https://github.com/etalab/udata-gouvfr/
[default-theme]: https://github.com/opendatateam/udata/tree/master/udata/theme/default/
