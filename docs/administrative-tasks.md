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

## Diagnostic

If you have some issues, start with:

```shell
$ udata info
```

This will display some useful details about your local configuration.

## Managing users

You can create a user with:

```shell
$ udata user create
```

You can also give a user administrative privileges with:

```shell
$ udata user set_admin <email>
```

## Purge data flagged as deleted

When users delete some data in udata,
it's only flagged as deleted and hidden in the frontend.
This allows the administrative team to undelete data in case of error.
To remove the data flagged as deleted once and for all, you need to purge them by
either launching the [appropriate jobs](#manage-jobs) or by executing the `purge` command.

```shell
$ udata purge
-> Purging datasets
-> Purging reuses
-> Purging organizations
```

Sometimes you need to purge only a given type of data. You can use the appropriate flags to do so:

```shell
# purge only datasets
$ udata purge --datasets
-> Purging datasets
# purge only reuses
$ udata purge --reuses
-> Purging reuses
# purge only organizations
$ udata purge --organizations
-> Purging organizations
```

**Warning**: these operations are permanents and irreversibles

**Note**: Users can't be fully purged because of the content they submitted which can't be orphaned.
This is why they are only anonymised.


## Manage jobs

Jobs are adminstrative tasks that can be run asynchronously on a worker
or synchronously through the shell.

You can list available jobs with:

```shell
$ udata job list
-> log-test
-> purge-organizations
-> purge-datasets
-> bump-metrics
-> purge-reuses
-> error-test
-> harvest
-> send-frequency-reminder
-> crawl-resources
-> count-tags
```

You can launch a job with:

```shell
# Run a job synchronously
$ udata job run job-name
# Run a job asynchronously (needs workers)
$ udata job run -d job-name
```

Some jobs require arguments and keywords arguments.
You can pass them with the `-a` for arguments and `-k`
for keyword arguments:

```shell
$ udata job run job-name -a arg1 arg2 -k key1=value key2=value
```

**Note**: this is a low level command.
Most of the time, you won't need it because there will be a dedicated command
to perform the task you need.
