FROM python:3.7

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash

RUN mkdir -p /tmp/
COPY requirements/ /tmp/requirements

RUN pip install -r /tmp/requirements/install.pip \
                -r /tmp/requirements/test.pip \
                -r /tmp/requirements/develop.pip \
                udata-gouvfr
