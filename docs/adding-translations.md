# Adding translations

There are translatable strings from both JS an Python.

We use [Crowdin][crowdin] for translations on the project.
First, you have to create an account.

After that you'll be able to reach the crowding pages for the project and interact with translations, ex:
- [udata crowdin page][crowdin-udata]
- [udata-front crowdin page][crowdin-udata-front]

!!! warning
    We only translate strings from the `main` and maintenance branches of the repository.
    Do not push languages on any other branch because merging translations is incredibly painful.


## Existing languages

The command `inv i18n` extract all these strings locally.
Pushing the changes on any branch will automatically update translatable strings on Crowdin.

Crowdin will submit pull requests on github each time translations are updated.

When pulling new translation in .po files, you should recompile translations with `inv i18nc` to generate .mo files.

## Proposing a new language

To propose a new language you need to submit a pull request:

* create a branch for the new translations (ex: `add-language-fr`)
* in this branch
    - add the language to the `LANGUAGES` setting
    - add the language to the const `languages` in webpack.config.js
* submit the pull request

Once it has been accepted, we will also create the new language translation in Crowdin.


[crowdin]: https://crowdin.com
[crowdin-udata]: https://crowdin.com/project/udata
[crowdin-udata-front]: https://crowdin.com/project/udata-front

## Adding translations in a plugin

You can also add or override some translations in your plugin (or your theme).
They should be located inside your module directory and follow this layout.
```
├── udata_plugin
│   ├── translations
│   │   ├── xx/LC_MESSAGES
│   │   │   └── udata-plugin.po
│   │   └── udata-plugin.pot
```

If the `translations` directory is present and contains some gettext-based translations(`po/mo` files),
they will be loaded. In the case of a theme, they will override existing ones.

The [dedicated cookiecutter template][cookiecutter-template] makes use of [Babel][] to extract string from your template
or compile them.

All commands below should be run from your plugin project root (where `pyproject.toml` is located).
Replace `udata_plugin` with your actual package name.

You can extract translations from your own templates using:

```bash
uv run pybabel extract -F babel.cfg -o udata_plugin/translations/udata-plugin.pot .
```

Then you can either add a new supported locale:

```bash
uv run pybabel init -l xx -i udata_plugin/translations/udata-plugin.pot -d udata_plugin/translations  # where xx is the locale you want to add. ex: fr
```

or update the existing ones:

```bash
uv run pybabel update -i udata_plugin/translations/udata-plugin.pot -d udata_plugin/translations
```

You can then translate the po file using the editor of your choice.
You could take a look at [Poedit][] or set up a Crowdin project if you want.

When translation is done, you can compile translations catalogs using:

```bash
uv run pybabel compile -d udata_plugin/translations
```

!!! warning
    Don't forget to compile and include translations in your theme distribution
    when you publish it.

[Babel]: http://babel.pocoo.org/
[cookiecutter-template]: https://github.com/opendatateam/cookiecutter-udata-theme
[Poedit]: https://poedit.net/
