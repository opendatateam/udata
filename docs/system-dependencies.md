# System dependencies

## Git and Python

First of all, you need [Git][] and [Python][] 2.7 (installed by default on OSX and many Linux distributions).

If you use `apt-get`, the package is named `git-core`.
If you prefer [Homebrew][] (OSX), the package is named `git`.

## Retrieving the sources

The sources of the project are on [Github][]:

```shell
$ git clone https://github.com/etalab/udata.git
```


## Other system dependencies

Libxml2 and LZMA are needed to install the python dependencies. On Ubuntu :
```shell
$ sudo apt-get install libxml2-dev libxslt1-dev liblzma-dev
```


## MongoDB, ElasticSearch and Redis

The project depends on [MongoDB][] 3.2+, [ElasticSearch][] 1.7 and [Redis][].

Installing these dependencies can be cumbersome given you operating system.
That's why we made a Docker container to ease that step.
You can either use it or install these dependencies by hand with the appropriated versions.

### With Docker

We will use [docker-compose][] to manage all that.
[Install Docker-Compose for your system][docker-compose-install].
On linux you should also [create a _docker_ group][docker-compose-group].
On Windows and MacOSX you will have to use a [docker-machine][].

Then start the services:

```shell
$ cd udata
$ docker-compose up
```

On the very first run it will download and install Docker images which takes a while depending of your connection.

!!! warning
    Test your _docker-compose_ is running successfully entering `curl http://locahost:9200`.
    It should output a JSON search response.
    If you have no output at all for too long,
    check the [IPv6 possible issue](https://github.com/docker/docker/issues/2174#issuecomment-35697655).

And install the [analysis-icu][] plugin for ElasticSearch:

```shell
$ docker-compose run search plugin install elasticsearch/elasticsearch-analysis-icu/2.7.0
$ docker-compose restart search
```

### By hand

It will depend on your configuration, join us on [Gitter][] if you have any issue. Try to match the exact version for ElasticSearch (1.7) given that version 2.+ is not backward-compatible!

!!! note
    Match the Analysis ICU plugin version to your elasticsearch version
    given those indicated in [the official repository][analysis-icu]

Once all dependencies are installed by hand, you can launch these services manually or use [Honcho][] with the proposed Procfile at the root of the repository (you'll have to uncomment related lines).

But first, let's install [local dependencies](local-dependencies.md)!


[mongodb]: https://www.mongodb.org/
[elasticsearch]: https://www.elastic.co/products/elasticsearch
[redis]: http://redis.io/
[honcho]: https://github.com/nickstenning/honcho
[gitter]: https://gitter.im/etalab/udata
[github]: https://github.com/etalab/udata
[homebrew]: http://brew.sh/
[python]: https://www.python.org/
[git]: https://git-scm.com/
[docker-compose]: https://docs.docker.com/compose/
[docker-compose-install]: https://docs.docker.com/compose/install/
[docker-compose-group]: https://docs.docker.com/engine/installation/linux/ubuntulinux/#create-a-docker-group
[docker-machine]: https://docs.docker.com/machine/overview/
[analysis-icu]: https://github.com/elastic/elasticsearch-analysis-icu
