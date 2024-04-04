# Creating a custom theme

The project as been developed from start with the goal to make it generic and reusable.
The theme engine is based on [Flask-Themes2][] so reading its documentation might help.

The difficulty of creating a new theme will depend on what you want to do:

- start from gouvfr and modify some style and colors ⇨ easy
- customize the layouts or how some part of udata is rendered ⇨ easy
- switch to another style framework ⇨ hard

## Project layout

You have different options for your theme layout.

You can either set your own [independent plugin theme](#independent-plugin-theme).
It means you are independent in your techno and don't rely on the
[udata-front][front-project] architecture.

You can also add your theme in [udata-front theme folder](#udata-front-based-theme) *(not recommended)*.
You don't need to have a separate plugin, but you will need to maintain your fork in sync with udata-front.

### Independent plugin theme

If you want to make your own independent plugin, you can follow this layout:

```
├── my_theme
│   ├── static
│   │   ├── index.css
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
- a `setup.py` exposing the package metadata (including the theme presence)
- a `setup.cfg` configuring setup commands (you can start from the one in `udata-front`)
- a `babel.cfg` configuring translations extractor

In the package directory (`my_theme` in this example), you need to have two files:

- `info.json` exposing metadata required by the theme loader
- `__init__.py` which is required by a Python package. It can be empty or contains hooks.

There can also be three directories:

- `static` containing static assets (images, styles, extra scripts...)
- `templates` containing the templates. You will need all the templates used in udata_front views
- `translations` containing the overriden translated strings (optional).


### udata-front based theme (not recommended)

If you want to use udata-front as a base and add your theme in the corresponding
directory, you can follow this layout:

```
udata_front
├── theme
│   ├── my_theme
│   │   ├── static
│   │   │   ├── index.css
│   │   │   ├── img
│   │   │   │   ├── flags
│   │   │   │   └── placeholders
│   │   ├── templates
│   │   │   └── *.html
│   │   ├── translations
│   │   │   ├── xx/LC_MESSAGES
│   │   │   │   └── my-theme.po
│   │   │   └── my-theme.pot
│   │   ├── info.json
│   │   └── __init__.py
│   └── gouvfr
│       └── ...
└── ...
```

Using this layout, you won't need to create files at the root level (`setup.py`, `babel.cfg`, etc.)
You will stil need the same files as the ones describe in the theme directory in
[independent plugin theme](#independent-plugin-theme).

!!! note
    These are proposal layout for standalone themes.
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

The `static` should contain an `index.css` file.

Then you are free to add any static assets required by your theme.

## Writing templates

We recommend starting from existing templates in `gouvfr` theme, copying them and iterating on those.
You can also start from scratch and implement the templates called in `udata_front` views.

You can reference static assets from your theme with the `theme_static` global function.
Take a look at [Jinja documentation][] for more information on writing jinja templates.

## Usage in udata

You can update your udata configuration file (probably `udata.cfg`) to add your new theme:
```
PLUGINS = ['front', 'my-theme']
THEME = 'my-theme'
```

When serving udata (`inv serve`), you should see your new theme live.

## Hooks

Your theme can also customize some behavior by using hooks in your ``__init__.py``.
Currently there are 2 available hooks:

- `theme.menu()` to register a custom main menu
- `theme.context()` to add extra context variable to some views

You can also expose extras menus using the `udata.app.nav` extension.
They will be available in the template context under the `nav` object.

```python
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
    You can see an example of advanced hooks usage in the [`front` plugin][front-hooks].

## Translations

You can also (and optionally) add or override some translations in you theme.
Take a look at [adding-translations](adding-translations.md) to set up translations.

## Avatars/identicon customization

Theme can provide settings for the avatar provider.

These settings take precedence over default values but are still overridable by local settings.

Simply declare your theme default values in your theme file:

```
AVATAR_INTERNAL_FOREGROUND = ['rgb(45,79,255)', 'rgb(254,180,44)']
AVATAR_INTERNAL_BACKGROUND = 'rgb(141,69,170)'

...
```

See the list of available settings [here](adapting-settings.md#avatarsidenticon-configuration).


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

- [`gouvfr`][front-project] as part of the [`front` plugin][front-project].


!!! note
    Don't hesitate to submit a pull-request to add your theme to this list.

## Help
You can ask for help on the [udata Github discussions][github-discussions].
Please report any difficulty you encounter with a dedicated [Github issue][github-new-issue].

[Flask-Themes2]: http://flask-themes2.readthedocs.io/en/latest/
[Jinja documentation]: https://jinja.pocoo.org/docs/
[github-new-issue]: https://github.com/opendatateam/udata/issues/new
[PyPI]: https://pypi.org/
[front-hooks]: https://github.com/etalab/udata-front/blob/master/udata_front/theme/__init__.py
[front-project]: https://github.com/etalab/udata-front/
[github-discussions]: https://github.com/opendatateam/udata/discussions/2721
