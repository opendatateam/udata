# Releasing

Every release is a git tag `vX.Y.Z` on `main`, following
[Python PEP 440 on versioning][pep440]. Between two tags, the version is computed by
`setuptools_scm` as the next patch plus the number of commits since the tag
(`17.6.1.dev1`), so you can always tell you are not on a stable release.

## Release process

udata uses a custom release script (`tag-version.sh`) to automate its release process.

To create a release, you need to:
- have administrator permission on the udata repository (to allow direct push)
- have the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`)

The steps to make a release are:

1. ensure translations are up to date
2. ensure the CircleCI build is successful on the main branch
3. run `./tag-version.sh X.Y.Z --dry-run` to preview the changelog and actions that will be performed
4. run `./tag-version.sh X.Y.Z` to perform the release. The script will automatically check that you are on the main branch, that your working copy is clean, and that you are up to date with the remote. It will then:
    - retrieve all commits since the last tag
    - sort commits alphabetically
    - detect breaking changes (commits with `!` before `:`) and put them first in bold
    - convert PR references (`#XXXX`) to markdown links
    - update CHANGELOG.md with the new version and date
    - commit the changelog update
    - create a git tag with the version (`vX.Y.Z`)
    - push both the commit and the tag to origin
    - create a GitHub release with the same changelog content
5. check on [github][] that the release has been created
6. wait for the [CircleCI][] build of the changelog commit on `main` to succeed — this is what
   publishes to PyPI, tagged builds don't publish
7. check on [PyPI](https://pypi.org/project/udata/#history) that the new release is present
8. celebrate!

## Breaking changes

There is no deprecation window: something that is removed is removed in the release that
removes it. What is guaranteed instead is that every breaking change ships in a **major**
version, and is announced.

Mark a breaking pull request with a `!` in its conventional commit prefix (`feat!:`,
`refactor!:`). `tag-version.sh` detects it, puts the entry first and in bold at the top of the
release notes. Read the [changelog](changelog.md) before upgrading: this is where breaking
changes, renamed settings and required migrations are documented.

[github]: https://github.com/opendatateam/udata
[CircleCI]: https://circleci.com/gh/opendatateam/udata
[pep440]: https://www.python.org/dev/peps/pep-0440/
