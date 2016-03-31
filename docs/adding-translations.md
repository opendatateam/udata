# Adding translations

There are translatable strings from both JS an Python.

We use [Transifex][transifex] for translations on the project.
First, you have to set a [~/.transifexrc][transifexrc].

!!! warning
    We only translate strings from the `master` branch of the repository, do not push languages on any other branch because merging translations is incredibly painful.

## Existing languages


The command `inv i18n` retrieve all these strings locally that you can then push to Transifex with the command `tx push -s`.

Then go to Transifex and translate new strings.

Once you did this, you can pull these strings with `tx pull` and then compile the retrieved files with `inv i18nc`.

Restart your server and new strings should be translated (don't forget to activate the right language!).


## Proposing a new language

Propose the new language on [Transifex][transifex], once accepted you can:

* translate on transifex
* create a branch for the new translations
* in this branch
    - add the language to the `LANGUAGES` setting
    - import the initial translations from transifex: `tx pull -r <language_code>`
    - add the corresponding flag in the default theme static assets (use one from [famfamfam flags][famfamfam-flags])
* check that it compiles with the command `inv i18nc` and that it is displayed as you expect on your local instance
* submit the pull request


[transifex]: https://www.transifex.com
[transifexrc]: http://docs.transifex.com/client/config/
[famfamfam-flags]: http://www.famfamfam.com/lab/icons/flags/
