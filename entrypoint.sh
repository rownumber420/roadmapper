#!/bin/bash
set -e

if [ -d /mnt/host-gemini ] && [ ! -f /home/appuser/.gemini/oauth_creds.json ]; then
  echo "Initializing gemini config from host mount..."
  mkdir -p /home/appuser/.gemini
  cp -r /mnt/host-gemini/. /home/appuser/.gemini/
  chown -R appuser:appuser /home/appuser/.gemini/
fi

if [ $# -gt 0 ] && [ "${1#-}" != "$1" ]; then
  exec gosu appuser python -m src.main "$@"
fi

exec gosu appuser "$@"
