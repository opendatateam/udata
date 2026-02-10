The prefered way to test udata is to use the [docker images][]
to easily have an up and ready udata instance.
Pre-configured udata with needed middlewares are given as examples.
You will need to install [docker][] and [docker-compose][] before getting started.

```shell
git clone https://github.com/opendatateam/docker-udata
cd docker-udata
docker compose up
```

The platform is available at [http://localhost:7000](http://localhost:7000).

You can initialise the database with fixtures and initialize the search index with
the `init` command. Using the udata docker container:
```shell
docker exec -it docker-udata-udata-1 udata init
```

You can take a look at the [udata Docker images readme][docker images] for more instructions
on udata configuration.

[docker images]: https://github.com/opendatateam/docker-udata
[docker-compose]: https://github.com/docker/compose
[docker]: https://www.docker.com/get-started/
