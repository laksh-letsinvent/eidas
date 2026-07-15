# eIDAS Portal — build & deploy

Phase 0 portal for the Wallet & QES lab. Built on the **same stack as the bio-authn `portal-next`** so the three portals are true siblings and Phases 2–6 extend this rather than replace it.

Stack: Next.js 16 · Tailwind v4 · shadcn (base-nova) · next-themes (dark-first, light toggle) · Space Grotesk / Inter / JetBrains Mono. Static export (`output: "export"`).

Brand: **eIDAS = violet** (`data-brand="eidas"`, accent `#8B5CF6` dark / `#7C3AED` light) — the third accent alongside Face Value cyan and Hard Copy burgundy. Violet dodges the accept/uncertain/reject semantic hues.

Target: **eidas.letsinvent.co.uk**

## What's here

```
portal/
  app/            # routes: / (Experiment), /atlas, /in-action, /try-it, /results
  components/     # AppShell (sidebar), MarkdownDoc, ComingSoon, ThemeProvider, ui/ (shadcn)
  lib/            # experiment.ts (loads md + strips internal tail), utils.ts
  content/        # ATLAS_EUDI.md + WALLET-QES-LAB-BRIEF.md (copied from the lab root)
  deploy/         # Caddyfile-eidas, deploy.sh
```

The Experiment page (`/`) renders `WALLET-QES-LAB-BRIEF.md` but drops everything from the "Open questions" heading onward and strips `[ASSUMED — confirm]` tags — single source, public-safe view. The Atlas (`/atlas`) renders verbatim. Three stub pages name what each later phase fills.

The design tokens live in `app/globals.css` — identical architecture to portal-next, with the eidas violet block appended (`:root[data-brand="eidas"]` and its `.light` variant).

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

Type-checks clean against the family's modules. The production build (Next 16 SWC) runs on the VM at deploy — it needs a fresh `npm install` there for the correct platform binaries.

## Deploy (Claude Code, on the VM)

The VM fronts every letsinvent.co.uk portal with a single shared **Caddy** instance (`/etc/caddy/Caddyfile`) — there is no nginx anywhere on this host. Each portal is one `server-name { ... }` block in that file; Caddy handles TLS itself (no certbot step). `eidas.letsinvent.co.uk` is already wired in, block starting `eidas.letsinvent.co.uk {` — `deploy/Caddyfile-eidas` is a reference copy of that block, not something you install standalone.

Prereqs on the VM: Caddy running with the shared Caddyfile, a DNS A record for `eidas.letsinvent.co.uk` → the VM, and Node 20+ (already present).

VM host/user aren't recorded here — ask Laksh or check prior deploy notes.

1. First-time only — if the `eidas.letsinvent.co.uk` block isn't in `/etc/caddy/Caddyfile` yet, append the contents of `deploy/Caddyfile-eidas` to it, then `caddy reload --config /etc/caddy/Caddyfile`.
2. Build and publish:
   ```bash
   ./deploy/deploy.sh user@your-vm-host
   ```
   Installs deps, builds `out/`, rsyncs to `/var/www/eidas/out/`, reloads Caddy.

## Updating content later

`content/` holds copies of the lab-root markdown. When the Atlas or brief changes:

```bash
cp ../ATLAS_EUDI.md ../WALLET-QES-LAB-BRIEF.md content/
npm run build
```

## When Phases 2+ land

Replace the three stub pages (`/in-action`, `/try-it`, `/results`) as each phase produces content. The AppShell nav, violet brand, and content-loading pattern stay; new pages are additive — same discipline as the frozen contracts in the build.
