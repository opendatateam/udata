# Launching tasks

There are two kinds of tasks: for production purpose or for development purpose.

## Tasks for production

You can get the documentation related to all tasks with:

```shell
$ udata -?
```

And then get the documentation for subtasks:

```shell
$ udata territories -?
```


## Tasks for development

You can get the documentation related to all tasks with:

```shell
$ inv -l
```

It might be required to update your dependencies to ensure compatibility.
A task is provided to automate it:

```shell
# Update dependencies
$ inv update
# Update dependencies and migrate data
$ inv update -d
```

It's advised to update your workspace when you pull upstream changes or switch branch:

```shell
# Update dependencies, migrate data, recompile translations...
$ inv update -d i18nc
```
