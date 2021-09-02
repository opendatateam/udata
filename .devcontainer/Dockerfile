FROM python:3.7

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash

ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN if [ "$USER_GID" != "1000" ] || [ "$USER_UID" != "1000" ]; then groupmod --gid $USER_GID node && usermod --uid $USER_UID --gid $USER_GID node; fi

RUN mkdir -p /tmp/
COPY requirements/ /tmp/requirements

RUN pip install -r /tmp/requirements/install.pip \
                -r /tmp/requirements/test.pip \
                -r /tmp/requirements/develop.pip \
                udata-gouvfr
