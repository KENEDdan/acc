# nginx / TLS setup

`nginx` terminates HTTPS for the app using a **Cloudflare Origin Certificate**
— free, valid for up to 15 years, and it's what Cloudflare's "Full (strict)"
SSL mode expects your origin server to present. This only works for traffic
that actually comes through Cloudflare (i.e. the domain's DNS records are
proxied — orange cloud — in Cloudflare), which is the setup here.

## One-time setup, on the droplet

1. In the Cloudflare dashboard for your domain: **SSL/TLS → Origin Server →
   Create Certificate**. Keep the defaults (RSA, 15 years, covers
   `example.org` and `*.example.org`). Cloudflare shows you two blocks of
   text — the certificate and the private key.
2. On the droplet, create the two files (paste each block exactly,
   including the `-----BEGIN...-----`/`-----END...-----` lines):
   ```
   nano nginx/certs/cloudflare-origin.pem   # the certificate block
   nano nginx/certs/cloudflare-origin.key   # the private key block
   chmod 600 nginx/certs/cloudflare-origin.key
   ```
3. In the Cloudflare dashboard: **SSL/TLS → Overview**, set the mode to
   **Full (strict)**.
4. Set `DOMAIN=example.org` in `.env` (no `https://`, no `www.` — the nginx
   template adds `www.$DOMAIN` itself).

`nginx/certs/` is gitignored — the private key never gets committed. Nothing
under `nginx/templates/` needs to change per-deploy; the domain name is
injected from `.env` at container startup.

## Why not Let's Encrypt / certbot directly?

It would also work, but needs a renewal cron job and briefly exposes an
HTTP-01 challenge. Since all real traffic already goes through Cloudflare's
proxy, a Cloudflare Origin Certificate is simpler (no renewal automation
needed for years) and keeps the origin's real IP better protected — Cloudflare
won't route to it at all unless the origin presents a cert Cloudflare trusts.
