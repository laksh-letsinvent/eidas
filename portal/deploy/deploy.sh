#!/usr/bin/env bash
# Build the eIDAS portal and publish it to the VM's web root.
# Run from the portal/ directory. Assumes SSH access to the VM and that
# nginx + certbot are already configured (see nginx-eidas.conf).
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
ssh "${REMOTE}" "sudo mkdir -p ${WEBROOT} && sudo chown -R \$(whoami) ${WEBROOT}"
rsync -az --delete out/ "${REMOTE}:${WEBROOT}/out/"

echo "==> Reloading nginx"
ssh "${REMOTE}" "sudo nginx -t && sudo systemctl reload nginx"

echo "==> Done. https://eidas.letsinvent.co.uk"
