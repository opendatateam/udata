 #!/usr/bin/env bash
set -e

echo "Setting up SSH directory"
SSH_PATH="$HOME/.ssh"
mkdir -p "$SSH_PATH"
chmod 700 "$SSH_PATH"

echo "Saving SSH key"
echo "$PRIVATE_KEY" > "$SSH_PATH/deploy_key"
chmod 600 "$SSH_PATH/deploy_key"

GIT_SSH_COMMAND="ssh -p ${PORT-22} -i $SSH_PATH/deploy_key"
if [ -n "$HOST_KEY" ]; then
    echo "Adding hosts key to known_hosts"
    echo "$HOST_KEY" >> "$SSH_PATH/known_hosts"
    chmod 600 "$SSH_PATH/known_hosts"
else
    echo "Disabling host key checking"
    GIT_SSH_COMMAND="$GIT_SSH_COMMAND -o StrictHostKeyChecking=no"
fi

APP_NAME="udata"

echo "Deploying $APP_NAME"
$GIT_SSH_COMMAND dokku@$HOST "ps:rebuild $APP_NAME"

URL="https://$APP_NAME.$HOST"
echo "::set-output name=url::$URL"
