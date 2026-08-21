# Deploying Kitchen

One-time setup on the VPS, alongside the existing nginx-served portfolio.
Nothing here touches the portfolio's own config.

## 1. DNS

Point an A record for `kitchen.sarthaksrivastava.tech` at the VPS before
touching certbot — it won't issue a cert for a name that doesn't resolve yet.

## 2. App container

```bash
git clone <this repo> /opt/kitchen
cd /opt/kitchen
cp .env.example .env   # fill in the real values
mkdir -p data
docker compose up -d --build
```

`docker-compose.yml` maps the container's port as `127.0.0.1:8420:8420`.
Inside the container, uvicorn still binds `0.0.0.0:8420` — that's required
for Docker's own port-publishing to work at all, a container process bound
to its own loopback is unreachable even from the host. The actual security
boundary is the `127.0.0.1:` prefix in the port mapping: Docker only
publishes that port on the host's loopback interface, so nothing outside the
box can reach it directly. nginx, running on the same host, is the only
thing that can reach `127.0.0.1:8420`.

The SQLite file lives at `./data/kitchen.db` on the host (bind-mounted into
the container at `/data`), not inside the container image — it survives
`docker compose up --build`.

## 3. Create the login

There's no signup endpoint on purpose. Create the one user by running the
CLI script inside the container:

```bash
docker compose exec kitchen python -m scripts.create_user sam
```

It prompts for a password twice and argon2-hashes it before writing to
SQLite.

## 4. nginx + TLS

```bash
cp deploy/nginx.conf.example /etc/nginx/sites-available/kitchen
ln -s /etc/nginx/sites-available/kitchen /etc/nginx/sites-enabled/kitchen
nginx -t && systemctl reload nginx
certbot --nginx -d kitchen.sarthaksrivastava.tech
```

certbot rewrites the server block in place to add the `listen 443 ssl`
half and an HTTP→HTTPS redirect. Re-run `nginx -t` after.

## 5. Brute-force protection

The app already locks an account out for 15 minutes after 5 failed
attempts, and the nginx config above rate-limits `/api/login` to 5
requests/minute per IP as a second layer. On top of that, install fail2ban
with an nginx auth-log jail scoped to `kitchen.sarthaksrivastava.tech` —
the subdomain will get scanned within days of the cert issuing.

## 6. Backups

```bash
# nightly cron, off-box
0 3 * * * sqlite3 /opt/kitchen/data/kitchen.db ".backup /path/to/offbox/kitchen-$(date +\%F).db"
```

It's one file — there's no excuse not to also **restore it once** to
confirm the backup actually works. An untested backup isn't a backup.

## 7. Verify

- `curl https://kitchen.sarthaksrivastava.tech/healthz` → `{"status":"ok"}`
- Visit the site on your phone, log in, "Add to Home Screen" — it should
  open fullscreen with no browser chrome.
