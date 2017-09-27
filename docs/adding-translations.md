# Adding translations

There are translatable strings from both JS an Python.

We use [Crowdin][crowdin] for translations on the project.
First, you have to create an account.

After that you'll be able to reach the [Crowdin page for the project][crowdin-udata] and interact with translations.

!!! warning
    We only translate strings from the `master` and maintenance branches of the repository.
    Do not push languages on any other branch because merging translations is incredibly painful.


## Existing languages

The command `inv i18n` extract all these strings locally.
Pushing the changes on any branch will automatically update translatable strings on Crowdin.

Crowdin will submit pull requests on github each time translations are updated.


## Proposing a new language

To propose a new language you need to submit a pull request:

* create a branch for the new translations (ex: `add-language-fr`)
* in this branch
    - add the language to the `LANGUAGES` setting
    - add the corresponding flag in the default theme static assets (use one from [famfamfam flags][famfamfam-flags])
* submit the pull request

Once it has been accepted, we will also create the new language translation in Crowdin.


[crowdin]: https://crowdin.com
[crowdin-udata]: https://crowdin.com/project/udata
[famfamfam-flags]: http://www.famfamfam.com/lab/icons/flags/
