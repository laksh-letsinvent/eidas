# eIDAS Portal — build & deploy

Phase 0 portal for the Wallet & QES lab. Next.js static export, same fabric as the bio-authn `portal-next` build so Phases 2–6 extend it rather than replace it. Renders the Atlas live and a cleaned public cut of the Experiment; three future pages are stubbed.

Target: **eidas.letsinvent.co.uk**

## What's here

```
portal/
  app/            # routes: / (Experiment), /atlas, /in-action, /try-it, /results
  components/     # Nav, Markdown renderer, ComingSoon
  lib/content.ts  # loads the two md files; strips the internal tail for the public Experiment cut
  content/        # ATLAS_EUDI.md + WALLET-QES-LAB-BRIEF.md (copied from the lab root)
  deploy/         # nginx-eidas.conf, deploy.sh
```

The Experiment page renders `WALLET-QES-LAB-BRIEF.md` but drops everything from the "Open questions" heading onward and strips `[ASSUMED — confirm]` tags — single source, public-safe view. The Atlas renders verbatim.

## Local preview

```bash
cd portal
npm install
npm run dev        # http://localhost:3000
```

## Build

```bash
npm run build      # produces ./out (static, no server needed)
```

Verified building clean on Next.js 15.5 / Node 22 — all six routes prerender. Note: the family standard is Next.js 16; bump `next` in package.json to `^16` to align. The app-router static-export API used here is unchanged across 15→16, so the bump is a version change, not a rewrite.

## Deploy (Claude Code, on the VM)

Prereqs on the VM: nginx, certbot, and a DNS A record for `eidas.letsinvent.co.uk` pointing at the VM.

1. Put the vhost in place and get TLS:
   ```bash
   sudo cp deploy/nginx-eidas.conf /etc/nginx/sites-available/eidas
   sudo ln -s /etc/nginx/sites-available/eidas /etc/nginx/sites-enabled/eidas
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d eidas.letsinvent.co.uk
   ```
2. Build and publish:
   ```bash
   ./deploy/deploy.sh user@your-vm-host
   ```
   The script installs deps, builds `out/`, rsyncs it to `/var/www/eidas/out/`, and reloads nginx.

## Updating content later

The two markdown files in `content/` are copies of the lab-root source. When the Atlas or brief changes, re-copy them and rebuild:

```bash
cp ../ATLAS_EUDI.md ../WALLET-QES-LAB-BRIEF.md content/
npm run build
```

(Phase 2+ will likely wire this into a single build step; for Phase 0 a manual copy is fine.)

## When Phases 2+ land

The three stub pages (`/in-action`, `/try-it`, `/results`) are placeholders that name what fills them and when. Replace their content as each phase produces it. The nav, brand, and content-loading pattern stay; new pages are additive — same discipline as the frozen contracts in the build.
