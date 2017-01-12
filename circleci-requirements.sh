#!/bin/bash
# Get the base branch for the right requirements
# Extracted from https://discuss.circleci.com/t/how-to-get-the-pull-request-upstream-branch/5496/3
# Until https://discuss.circleci.com/t/expose-the-title-and-upstream-branch-of-a-pull-request-build-as-an-env/5475/1
# is implemented

# Set a default in case we run into rate limit restrictions
BASE_BRANCH="master"
if [[ $CIRCLE_PR_NUMBER ]]; then
  BASE_BRANCH=$(curl -fsSL https://api.github.com/repos/$CIRCLE_PROJECT_USERNAME/$CIRCLE_PROJECT_REPONAME/pulls/$CIRCLE_PR_NUMBER | jq -r '.base.ref')
elif [[ $CIRCLE_TAG ]]; then
  BASE_BRANCH='master'
else
  BASE_BRANCH=$CIRCLE_BRANCH
fi
if [[ $BASE_BRANCH == "dev" ]]; then
    # Test against last published  pre version
    pip install -U --pre udata[test]
else
    # Test against last published stable version
    pip install -U udata[test]
fi
pip install -e . invoke
