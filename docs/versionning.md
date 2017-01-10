# Versionning and deprecations

## Versionning process

UData uses [semantic versionning][semver] to publish its published releases.

### Branches management

There is two main branches on the [UData git repository][github]: `master` and `dev`

The `master` is the stable development branch on which:

- bug fixes should occurs (unless is only present on `dev` branch)
- bugfix or security upgrades (only) are done
- translations are done
- releases are done

The `dev` branch hosts:

- the incoming new features (and their bug fixes)
- the factoring
- the dependencies upgrades
- the bug fixes associated to these

There is always at least one minor version between the `dev` and the `master branch`
(*ie.* `1.0.2.dev` on `master` and `1.1.0.dev` on `dev`).


Every version has a git tag `X.Y.Z` and then when bug fixes need to be applied
without publishing new changes, there will be a version branch `X.Y`

The content of each version (expected or real) is tracked trough [issues][], [pull requests][pulls]
and [milestones][].


### Merging

Regular imports of changes from `master` branch are done into the `dev` branch
in the form of pull requests (ideally from a branch named `merge-master-YYYY-MM-DD`).

Merge from `dev` to `master` branch are done when the dev branch is considered stable
and should not receive new features.


## Releasing

UData uses [Bump'R][bumpr] to perform its release process.

To be perform a release, you'll need to:

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
    - set a git tag with the version (`X.Y.Z`)
    - perform next iterationreplacements (increased dev version, URLs)
    - prepare the changelog for the next iteration
    - commit
    - push (commits and tags)
7. check on [github][] that everything has been pushed
8. wait for [CircleCI][] tagged build to succeed
9. check on [PyPI](https://pypi.python.org/pypi/udata) that the new release is present
10. celebrate

### Fixing an old version

If this is first bug fix, create a branch associated with the minor version
(*ie.* `X.Y` when the tag is `X.Y.0`) and and publish it:

```shell
git checkout -b X.Y X.Y.0
git push -u origin X.Y
```

If the branch already exists, just switch on it:

```shell
git checkout X.Y
```

Perform a pull request from this branch:

```shell
git checkout -b my-old-fix
# fix fix fix
git commit
git push -u myrepository my-old-fix
```

## Deprecation policy

**When it's possible** deprecation are signaled 2 minor versions before being really dropped.
It's up to the developpers and system administrators to read the [changelog](changelog.md) before upgrading
(deprecations and breaking changes are signaled).

[bumpr]: https://github.com/noirbizarre/bumpr/
[semver]: http://semver.org/
[github]: https://github.com/opendatateam/udata
[issues]: https://github.com/opendatateam/udata/issues
[pulls]: https://github.com/opendatateam/udata/pulls
[milestones]: https://github.com/opendatateam/udata/milestones
[CircleCI]: https://circleci.com/gh/opendatateam/udata
