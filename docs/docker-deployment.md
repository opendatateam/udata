# Docker deployment

This documents the [Docker][] way to deploy udata.
If you are intending to perform a classic deployment on a server, you should look at the [Installation section](installation.md).

udata and its extensions are packaged and distributed as [Docker images][].
Head directly to [the dedicated repository][docker-repository] for an up to date documentation and [configuration samples][].

## Developing on your machine

[Docker Compose][] makes it easy to spawn [system dependencies](system-dependencies.md) out of the box by running the following command:

```shell
docker-compose up
```

[Docker]: https://www.docker.com/
[Docker images]: https://hub.docker.com/r/udata/udata/
[docker-repository]: https://github.com/opendatateam/docker-udata
[docker compose]: https://docs.docker.com/compose/
[configuration samples]: https://github.com/opendatateam/docker-udata/tree/master/samples
