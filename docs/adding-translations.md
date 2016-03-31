# Adding translations

There are translatable strings from both JS an Python.

We use [Transifex][transifex] for translations on the project.
First, you have to set a [~/.transifexrc][transifexrc].

The command `inv i18n` retrieve all these strings locally that you can then push to Transifex with the command `tx push -s`.

Then go to Transifex and translate new strings.

Once you did this, you can pull these strings with `tx pull -f` and then compile the retrieved files with `inv i18nc`.

Restart your server and new strings should be translated (don't forget to activate the right language!).

[transifex]: https://www.transifex.com
[transifexrc]: http://docs.transifex.com/client/config/
