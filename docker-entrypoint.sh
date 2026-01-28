#!/bin/sh
set -e

# Definition of the secret file path
# Defaults to /run/secrets/flet_secret if not set via env
: ${FLET_SECRET_FILE:=/run/secrets/flet_secret}

# Check if the secret file exists
if [ -f "$FLET_SECRET_FILE" ]; then
    echo "Files based secret found at $FLET_SECRET_FILE. Exporting FLET_SECRET..."
    export FLET_SECRET=$(cat "$FLET_SECRET_FILE")
fi

# Execute the CMD passed to the docker container
exec "$@"
