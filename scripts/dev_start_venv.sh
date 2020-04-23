#!/bin/bash

UDATA_VENV="venv"

# enter virtual env
source $UDATA_VENV/bin/activate

# sync with origin/master
git pull origin master