# Versionning and deprecations

## Versionning process

UData follows [Python PEP 440 on versionning][pep440] to version its published releases.

### Branches management

There is a main branch on the [UData git repository][github], `master`,
and some maintenance branches `vX.Y`

The `master` is the stable development branch on which:

- bug fixes should occurs (unless is only present on a maintenance branch)
- security upgrades are done (unless is only necessary on a maintenance branch)
- the incoming new features (and their bug fixes)
- the refactoring
- the dependencies upgrades
- translations are done
- releases are done

The `vX.Y` maintenance branches host:

- the bug fixes and security upgrades associated to theses versions only
- the backported bug fixes and security upgrades

Every minor version has a maintenance branch `vX.Y` and every version has a git tag `vX.Y.Z`.

Otherwise the version is `X.Y.Z.dev` (1.1.7.dev)
so you can easily see when you are not using a stable release.

The content of each version (expected or real) is tracked trough [issues][], [pull requests][pulls]
and [milestones][].


## Releasing

UData uses [Bump'R][bumpr] to perform its release process.

To perform a release, you'll need to:

- have administrator permission on the UData repository (to allow direct push)
- have a working development environment up to date with the `master` branch
- have `bumpr` installed

The step to perform a release are:

1. fetch latest changes from upstream repository
2. ensure translations are up to date
3. ensure CircleCI build is successful on master branch
4. ensure your working copy is clean
5. run `bumpr -d -v` to preview the actions performed and the changes
6. run `bumpr` to perform the release. This will:
    - clean up remaining build artifacts
    - execute tests
    - perform a full packaging (to ensure its working)
    - perform replacements (bumped version, URLs)
    - set the changelog version and date
    - commit
    - set a git tag with the version (`vX.Y.Z`)
    - perform next iterationreplacements (increased dev version, URLs)
    - prepare the changelog for the next iteration
    - commit
    - push (commits and tags)
7. check on [github][] that everything has been pushed
8. wait for [CircleCI][] tagged build to succeed
9. check on [PyPI](https://pypi.python.org/pypi/udata) that the new release is present
10. celebrate

## Branching

We need to branch the master each time a minor version development cycle starts:

- create a branch for the current minor version. **ex**: if the current master version is `1.1.8.dev`, create a `v1.1` branch with `git checkout -b v1.1`
- publish the branch to the official repository: `git push -u origin vX.Y`
- get the `master` branch back: `git checkout master`
- increment the version in `udata/__init__.py`: **ex** `1.1.8.dev` become `1.2.0.dev`

### Fixing an old version

Switch on the maintenance branch you need:

```shell
git checkout vX.Y
```

Create a new branch from the maintenance one and
perform a pull request from it:

```shell
git checkout -b my-fix
# fix fix fix
git commit
git push -u myrepository my-fix
```

## Feature branches

Sometimes a new feature or an EPIC requires more than one pull request and a lot of testing.
For these cases, it's not desirable to use the `master` branch to test until it's stable because we want to keep the `master` branch as stable as possible.

To handle these cases we are using feature branches, named like `feature/my-feature`. These branches will build on CircleCI and publish [local versions](pep440-local) packages on PyPI.

The local identifier will be the feature branch name so the version number will be `X.Y.Z.devBBB+my-feature` where `BBB` is the build number.

## Deprecation policy

**When it's possible** deprecation are signaled 2 minor versions before being really dropped.
It's up to the developpers and system administrators to read the [changelog](changelog.md) before upgrading
(deprecations and breaking changes are signaled).

[bumpr]: https://github.com/noirbizarre/bumpr/
[github]: https://github.com/opendatateam/udata
[issues]: https://github.com/opendatateam/udata/issues
[pulls]: https://github.com/opendatateam/udata/pulls
[milestones]: https://github.com/opendatateam/udata/milestones
[CircleCI]: https://circleci.com/gh/opendatateam/udata
[pep440]: https://www.python.org/dev/peps/pep-0440/
[pep440-local]: https://www.python.org/dev/peps/pep-0440/#local-version-segments
