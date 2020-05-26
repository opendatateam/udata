<p align="center"><img src="https://i.imgur.com/rlRox1c.png"></p>

udata
=====

[![Build status][circleci-badge]][circleci-url]
[![Python Requirements Status][requires-io-badge]][requires-io-url]
[![JavaScript Dependencies Status][david-dm-badge]][david-dm-url]
[![JavaScript Development Dependencies Status][david-dm-dev-badge]][david-dm-dev-url]
[![Translation progress][crowdin-badge]][crowdin-url]
[![Read the documentation][readthedocs-badge]][readthedocs-url]
[![Join the chat at https://gitter.im/opendatateam/udata][gitter-badge]][gitter-url]

Customizable and skinnable social platform dedicated to (open)data.

The [full documentation][readthedocs-url] is hosted on Read the Docs.

udata is maintained by [Etalab](https://www.etalab.gouv.fr/), the
french public agency in charge of open data.  Etalab is responsible
for publishing udata's roadmap and for building consensus around it.

It is collectively taken care of by members of the
[OpenDataTeam](https://github.com/opendatateam).

[circleci-url]: https://circleci.com/gh/opendatateam/udata
[circleci-badge]: https://circleci.com/gh/opendatateam/udata.svg?style=shield
[requires-io-url]: https://requires.io/github/opendatateam/udata/requirements/?branch=master
[requires-io-badge]: https://requires.io/github/opendatateam/udata/requirements.svg?branch=master
[david-dm-url]: https://david-dm.org/opendatateam/udata
[david-dm-badge]: https://img.shields.io/david/opendatateam/udata/status.svg
[david-dm-dev-url]: https://david-dm.org/opendatateam/udata?type=dev
[david-dm-dev-badge]: https://david-dm.org/opendatateam/udata/dev-status.svg
[gitter-badge]: https://badges.gitter.im/Join%20Chat.svg
[gitter-url]: https://gitter.im/opendatateam/udata
[readthedocs-badge]: https://readthedocs.org/projects/udata/badge/?version=latest
[readthedocs-url]: https://udata.readthedocs.io/en/latest/
[crowdin-badge]: https://d322cqt584bo4o.cloudfront.net/udata/localized.svg
[crowdin-url]: https://crowdin.com/project/udata


--------

#### dev environment

- _notes :_

  - _Python 3.* must be installed_
  - _Docker daemon must be running_

- chained installation with scripts

  ```bash
  git clone https://github.com/co-demos/udata.git udata
  cd udata
  sh ./scripts/dev_setup_env.sh
  ```

- run with scripts (only if dev environment is set up)

  ```bash
  sh ./scripts/dev_start_dev_env.sh
  ```
