# Releasing

Every release is a git tag `vX.Y.Z` on `main`, following
[Python PEP 440 on versioning][pep440]. Between two tags, the version is computed by
`setuptools_scm` as the next patch plus the number of commits since the tag
(`17.6.1.dev1`), so you can always tell you are not on a stable release.

## Release process

A release goes through a pull request, prepared and tagged by the actions of
`.github/actions/release`.

1. ensure translations are up to date
2. ensure the [CI][] build is successful on the main branch
3. run the [Release][prepare] workflow with the version `X.Y.Z` (and the numbers of
   the PRs to mark as breaking, if any), from the Actions tab or with
   `gh workflow run release.yml -f version=X.Y.Z`. It:
    - retrieves all commits since the last tag
    - sorts commits alphabetically
    - detects breaking changes (commits with `!` before `:`) and puts them first in bold
    - converts PR references (`#XXXX`) to markdown links
    - adds the version and its date to `CHANGELOG.md`, updates `publiccode.yml`
    - opens the "Bump version X.Y.Z" pull request
4. review the pull request and squash merge it. If something is merged on `main` in the
   meantime, update the branch (merge or rebase `main`): the changelog of the release is
   then regenerated with the new PRs, keeping its date and the PRs shown as breaking. A
   wording edited by hand in the changelog is kept as long as no new PR comes in.
5. the [CI][] build of the merge commit on `main` then creates the `vX.Y.Z` tag and the
   GitHub release, whose notes are the `X.Y.Z` section of the changelog, and publishes the
   release to PyPI. If this build fails, re-run it: a later commit never tags a release.
6. check on [PyPI](https://pypi.org/project/udata/#history) that the new release is present
7. celebrate!

## Breaking changes

There is no deprecation window: something that is removed is removed in the release that
removes it. What is guaranteed instead is that every breaking change ships in a **major**
version, and is announced.

Mark a breaking pull request with a `!` in its conventional commit prefix (`feat!:`,
`refactor!:`). The release workflow detects it, puts the entry first and in bold at the top of the
release notes. Read the [changelog](changelog.md) before upgrading: this is where breaking
changes, renamed settings and required migrations are documented.

[prepare]: https://github.com/opendatateam/udata/actions/workflows/release.yml
[CI]: https://github.com/opendatateam/udata/actions/workflows/ci.yml
[pep440]: https://www.python.org/dev/peps/pep-0440/
