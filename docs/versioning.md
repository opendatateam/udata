# Versioning and deprecating

## Versioning process

udata follows [Python PEP 440 on versioning][pep440] to version its published releases.

### Branches management

There is a main branch on the [udata git repository][github], `main` and some temporary feature branches.

The `main` is the stable development branch on which:

- bug fixes should occur (unless the bug is only present on a maintenance branch)
- security upgrades are done (unless only necessary on a maintenance branch)
- the incoming new features (and their bug fixes)
- the refactoring
- the dependencies upgrades
- translations are done
- releases are done

Every version has a git tag `vX.Y.Z`.

Otherwise the version is `X.Y.Z.dev` (1.1.7.dev) so you can easily see when you are not using a stable release.

The contents of each version (expected or real) is tracked trough [issues][], [pull requests][pulls] and sometimes [discussions][].


## Releasing

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
6. wait for [CircleCI][] tagged build to succeed
7. check on [PyPI](https://pypi.org/project/udata/#history) that the new release is present
8. celebrate!

## Feature branches

Sometimes a new feature or an EPIC requires more than one pull request and a lot of testing.
For these cases, it's not desirable to use the `main` branch to test until it's stable because we want to keep the `main` branch as stable as possible.

To handle these cases we are using feature branches, named like `feature/my-feature`. These branches will build on CircleCI and produce a [local version](pep440-local) package.

The local identifier will be the feature branch name so the version number will be `X.Y.Z.devBBB+my-feature` where `BBB` is the build number.

## Deprecation policy

**When it's possible** deprecations are published 2 minor versions before being really dropped.
It's up to the developers and system administrators to read the [changelog](changelog.md) before upgrading
(deprecations and breaking changes are published).

[github]: https://github.com/opendatateam/udata
[issues]: https://github.com/opendatateam/udata/issues
[pulls]: https://github.com/opendatateam/udata/pulls
[discussions]: https://github.com/opendatateam/udata/discussions
[CircleCI]: https://circleci.com/gh/opendatateam/udata
[pep440]: https://www.python.org/dev/peps/pep-0440/
[pep440-local]: https://www.python.org/dev/peps/pep-0440/#local-version-segments
