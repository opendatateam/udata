# Launching tasks

udata provides a command line interface for most of the administrative tasks.

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

### Check db integrity

```shell
$ udata db check-integrity
```

This will output a diagnosis with the most common sources of lack of integrity in udata's model. No fix is applied by this command.

## Managing users

You can create a user with:

```shell
$ udata user create
```

You can also give a user administrative privileges with:

```shell
$ udata user set-admin <email>
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
log-test
purge-organizations
purge-datasets
bump-metrics
purge-reuses
error-test
harvest
send-frequency-reminder
crawl-resources
count-tags
```

You can launch a job with:

```shell
# Run a job synchronously
$ udata job run job-name
# Run a job asynchronously (needs workers)
$ udata job run -d job-name
```

Some jobs require arguments and keywords arguments.
You can pass them as arguments too:

```shell
$ udata job run job-name arg1 arg2 key1=value key2=value
```

**Note**: this is a low level command.
Most of the time, you won't need it because there will be a dedicated command
to perform the task you need.

You can also schedule or unschedule jobs (and list scheduled jobs):

```shell
$ udata job scheduled
# No scheduled jobs
$ udata job schedule "0 * * * *" count-tags
➢ Scheduled Job count-tags with the following crontab: 0 * * * *
$ udata job scheduled
Count tags: count-tags ↦ 0 * * * *
# Same command to reschedule
$ udata job schedule "1 * * * *" count-tags
➢ Scheduled Job count-tags with the following crontab: 1 * * * *
$ udata job scheduled
Count tags: count-tags ↦ 1 * * * *
$ udata job unschedule count-tags
➢ Unscheduled Job count-tags with the following crontab: 0 * * * *
$ udata job scheduled
# No scheduled jobs
```

Because a job can be scheduled multiple times with different parameters,
you need to provide the same parameters to unschedule:

```shell
$ udata job schedule my-job "0 * * * *" arg key=value
➢ Scheduled Job my-job(arg, key=value) with the following crontab: 0 * * * *
$ udata job unschedule my-job
✘ No scheduled job match Job my-job
$ udata job unschedule my-job arg key=value
➢ Unscheduled Job my-job(arg, key=value) with the following crontab: 0 * * * *
```

## Reindexing data

Sometimes, you need to reindex data (in case of model breaking changes, workers defect...).
You can use the `udata search index` command to do so.

By default, this command indexes all documents to the existing indices.

This command supports indexation of all models without arguments or particular model with model names as arguments:

```shell
# Index everything
udata search index
# Only index reuses and organizations
udata search index reuses organizations
```



It's possible to reindex from scratch, indexing documents to a new index.
```shell
time udata search index --reindex true
```
The target index name will be time-based, ex: dataset-2022-02-20-20-02.

**Warning**: After full reindexation execution, you'll need to change the alias on the search service to use the new index.


It's possible to index or reindex only last modified documents.

```shell
time udata search index -f 2022-02-20-20-02
```

## Workers

Start a worker with:

```shell
$ udata worker start
```

See all waiting Celery tasks across all workers:

```shell
$ udata worker status
```

Display waiting tasks in a Munin plugin compatible format (you can use the provided [Munin plugin][munin-plugin]):

```shell
$ udata worker status --munin -q default
$ udata worker status --munin-config -q default
```

[munin-plugin]: https://github.com/etalab/munin-plugins/tree/master/udata


## Cache

Flush the cache with:

```shell
$ udata cache flush
```
