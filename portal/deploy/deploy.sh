#!/usr/bin/env bash
# Build the eIDAS portal and publish it to the VM's web root.
# Run from the portal/ directory. Assumes SSH access to the VM and that
# the eidas.letsinvent.co.uk block is already in the shared Caddyfile
# (see Caddyfile-eidas — it's one block among several sibling portals
# in /etc/caddy/Caddyfile, not a standalone config to install).
#
# Usage:
#   ./deploy/deploy.sh user@vm-host
#
set -euo pipefail

REMOTE="${1:?Usage: ./deploy/deploy.sh user@vm-host}"
WEBROOT="/var/www/eidas"

echo "==> Installing dependencies"
npm install --no-audit --no-fund

echo "==> Building static export"
npm run build            # produces ./out

echo "==> Syncing out/ to ${REMOTE}:${WEBROOT}/out"
ssh "${REMOTE}" "mkdir -p ${WEBROOT}"
rsync -az --delete out/ "${REMOTE}:${WEBROOT}/out/"

echo "==> Reloading Caddy"
ssh "${REMOTE}" "caddy reload --config /etc/caddy/Caddyfile"

echo "==> Done. https://eidas.letsinvent.co.uk"
