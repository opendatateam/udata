# Contributing guide

**Hello fellow developer/hacker/citizen/peer!**

The udata project welcomes, and depends, on contributions from developers and users in the open source community. Contributions can be made in a number of ways, a few examples are:

* Code patches via pull requests
* Documentation improvements
* Bug reports and patch reviews

We welcome improvements from developers of all skill levels.

## Ethics

This project operates under the W3C's
[Code of Ethics and Professional Conduct][code-ethics]:

> W3C is a growing and global community where participants choose to work
> together, and in that process experience differences in language, location,
> nationality, and experience. In such a diverse environment, misunderstandings
> and disagreements happen, which in most cases can be resolved informally. In
> rare cases, however, behavior can intimidate, harass, or otherwise disrupt one
> or more people in the community, which W3C will not tolerate.
>
> A Code of Ethics and Professional Conduct is useful to define accepted and
> acceptable behaviors and to promote high standards of professional
> practice. It also provides a benchmark for self evaluation and acts as a
> vehicle for better identity of the organization.

We hope that our community group act according to these guidelines, and that
participants hold each other to these high standards. If you have any questions
or are worried that the code isn't being followed, please contact the owner of the repository.

## Language

The development language is English. All comments and documentation should be written in English, so that we don't end up with “frenghish” methods, and so we can share our learnings with developers around the world.

## Process

We’re really happy to accept contributions from the community, that’s the main reason why we open-sourced it! There are many ways to contribute, even if you’re not a technical person.

We’re using the infamous [simplified Github workflow][simplified-github-workflow] to accept modifications (even internally),
basically you’ll have to:

* create an issue related to the problem you want to fix (good for traceability and cross-reference)
* fork the repository
* create a branch (optionally with the reference to the issue in the name)
* hack hack hack
* commit incrementally with readable and detailed commit messages
* add the change to the `CHANGELOG.md` file if appropriated
* submit a pull-request against the right branch of this repository:
    * `master` for new features or bug fixes for the current state
    * `vX.Y` for bugfixes or backports on previous versions

We’ll take care of tagging your issue with the appropriated labels and answer within a week (hopefully less!) to the problem you encounter.

If you’re not familiar with open-source workflows or our set of technologies, do not hesitate to ask for help! We can mentor you or propose good first bugs.

**NOTE**: If you are fixing an existing issue,
don't forget to end your commit message with `(fix #XXX)`
where `XXX` is the original issue number. You can also add
`fix #XXX` in the PR description. This will improve the tracability
and will magicaly close the issue as soon as the commit is merged.

### Merging

When the PR has been approved (at least once), you are free to merge it
in master. We have a squash & merge strategy and pay attention to having
a clean commit message. You can then delete the branch. If linked with
an issue, the issue should be closed automatically.

## Discussing strategies

We’re trying to develop this project in the open as much as possible. We created a dedicated [Github discussions][github-discussions] where we discuss each new strategic change and invite the community to give a valuable feedback. You’re encouraged to join and participate.

## Code guides

### Python style guide

We follow the PEP-0008 and PEP-0257 as much as possible in the respect of PEP-0020.

On top of that, we apply the [Python Style Guide][py-style-guide] from Google.
Linting, formatting and import sorting are done automatically by [Ruff](https://docs.astral.sh/ruff/) launched by a pre-commit hook. So, before contributing to the repository, it is necessary to initialize the pre-commit hooks:
```bash
pre-commit install
```
Once this is done, code formatting and linting, as well as import sorting, will be automatically checked before each commit.

If you cannot use pre-commit, it is necessary to format, lint, and sort imports with [Ruff](https://docs.astral.sh/ruff/) before committing:
```bash
ruff check --fix .
ruff format .
```

> WARNING: running `ruff` on the codebase will lint and format all of it, whereas using `pre-commit` will
  only be done on the staged files.

### JavaScript style guide

We follow the [JavaScript styleguide][js-styleguide] from airbnb.

### HTML and CSS code guide

We follow @mdo's [code guide][code-guide].

### Documentation syntax

We try to stay as close as possible to [CommonMark][] but use default [extensions proposed by MkDocs][extensions-mkdocs].


[code-ethics]: https://www.w3.org/Consortium/cepc
[simplified-github-workflow]: http://scottchacon.com/2011/08/31/github-flow.html
[PEP-0008]: https://www.python.org/dev/peps/pep-0008/
[PEP-0257]: https://www.python.org/dev/peps/pep-0257/
[PEP-0020]: https://www.python.org/dev/peps/pep-0020/
[py-style-guide]: https://google.github.io/styleguide/pyguide.html
[js-styleguide]: https://github.com/airbnb/javascript
[code-guide]: http://codeguide.co/
[commonmark]: http://commonmark.org/
[extensions-mkdocs]: http://www.mkdocs.org/user-guide/writing-your-docs/
[github-discussions]: https://github.com/opendatateam/udata/discussions/2721
