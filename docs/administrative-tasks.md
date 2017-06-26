# Launching tasks

uData provides a command line interface for most of the administrative tasks.

You can get the documentation related to all tasks with:

```shell
$ udata -?
```

And then get the documentation for subtasks:

```shell
$ udata user -?
```
## Managing users

You can create a user with:

```shell
$ udata user create
```

You can also give a user administrative privileges with:

```shell
$ udata user set_admin <email>
```
