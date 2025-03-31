# Versioning and deprecating

## Versioning process

udata follows [Python PEP 440 on versioning][pep440] to version its published releases.

### Branches management

There is a main branch on the [udata git repository][github], `master` and some temporary feature branches.

The `master` is the stable development branch on which:

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

udata uses [Bump'X][https://github.com/datagouv/bumpx] as its release process.

To create a release, you need to:

- have administrator permission on the udata repository (to allow direct push)
- have a working development environment up to date with the `master` branch
- have `bumpx` installed

The step to make a release are:

1. fetch latest changes from upstream repository
2. ensure translations are up to date
3. ensure the CircleCI build is successful on master branch
4. ensure your working copy is clean
5. run `bumpx -d -v` to preview the actions performed and the changes
6. run `bumpx` to perform the release.  This will:
    - clean up remaining build artifacts
    - execute tests
    - perform a full packaging (to ensure it is working)
    - perform replacements (bumped version, URLs)
    - set the changelog version and date
    - commit
    - set a git tag with the version (`vX.Y.Z`)
    - perform next iteration replacements (increased dev version, URLs)
    - prepare the changelog for the next iteration
    - commit
    - push (commits and tags)
7. check on [github][] that everything has been pushed
8. wait for [CircleCI][] tagged build to succeed
9. check on [PyPI](https://pypi.org/project/udata/#history) that the new release is present
10. celebrate!

## Feature branches

Sometimes a new feature or an EPIC requires more than one pull request and a lot of testing.
For these cases, it's not desirable to use the `master` branch to test until it's stable because we want to keep the `master` branch as stable as possible.

To handle these cases we are using feature branches, named like `feature/my-feature`. These branches will build on CircleCI and produce a [local version](pep440-local) package.

The local identifier will be the feature branch name so the version number will be `X.Y.Z.devBBB+my-feature` where `BBB` is the build number.

## Deprecation policy

**When it's possible** deprecations are published 2 minor versions before being really dropped.
It's up to the developers and system administrators to read the [changelog](changelog.md) before upgrading
(deprecations and breaking changes are published).

[bumpx]: https://github.com/datagouv/bumpx
[github]: https://github.com/opendatateam/udata
[issues]: https://github.com/opendatateam/udata/issues
[pulls]: https://github.com/opendatateam/udata/pulls
[discussions]: https://github.com/opendatateam/udata/discussions
[CircleCI]: https://circleci.com/gh/opendatateam/udata
[pep440]: https://www.python.org/dev/peps/pep-0440/
[pep440-local]: https://www.python.org/dev/peps/pep-0440/#local-version-segments
