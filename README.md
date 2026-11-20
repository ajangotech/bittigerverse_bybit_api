# BitTiger Bybit P2P API — Independent Python Microservices

This version runs the API as **two completely separate Python applications in two separate Docker containers**:

- `price-limit` → its own Python app, image, container, cache and Gunicorn process. It serves only `POST /api/ad-price-limit`.
- `main-api` → a separate Python app, image, container and Gunicorn process. It serves every other API endpoint.
- `nginx` → public reverse proxy that sends each request to the correct container.

There is **no `SERVICE_ROLE` switch and no shared `app.py`** between the two services. Each service has its own `app.py`, `common.py`, `Dockerfile`, Python process and container.

## Structure

```text
services/
├── price-limit/
│   ├── app.py
│   ├── common.py
│   └── Dockerfile
└── main-api/
    ├── app.py
    ├── common.py
    └── Dockerfile
```

The small `common.py` files are copied into each service so the containers remain independently buildable.

## Public route mapping

| Public endpoint | Python application | Docker container |
|---|---|---|
| `/api/ad-price-limit` | `services/price-limit/app.py` | `bittiger-price-limit` |
| `/api/update-ad` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/payment-types` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/balance` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/account` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/ads` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/ad-details` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/remove-ad` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/orders` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/reference-price` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/pending-orders` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/analyze-market` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/online-ads` | `services/main-api/app.py` | `bittiger-main-api` |
| `/api/mark-as-paid` | `services/main-api/app.py` | `bittiger-main-api` |

## Deploy

On Ubuntu:

```bash
sudo bash scripts/install-docker-ubuntu.sh

cp .env.example .env
nano .env

bash scripts/deploy.sh
```

Or manually:

```bash
docker compose build
docker compose up -d
```

## Verify

```bash
docker compose ps

curl http://127.0.0.1/health
curl http://127.0.0.1/
```

Check the two Python applications independently:

```bash
docker compose exec price-limit python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8090/health').read().decode())"

docker compose exec main-api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8090/health').read().decode())"
```

Logs:

```bash
docker compose logs -f price-limit
docker compose logs -f main-api
docker compose logs -f nginx
```

Restart only one service:

```bash
docker compose restart price-limit
docker compose restart main-api
```

Rebuild only one application:

```bash
docker compose build price-limit
docker compose up -d price-limit

docker compose build main-api
docker compose up -d main-api
```

## Important

The price-limit cache remains local to the `price-limit` container. Because that service uses one Gunicorn worker with multiple threads, the in-memory cache and lock are shared by the threads inside that container.

The main API does not load the price-limit route at all, and the price-limit application does not load the other API routes.

Bybit credentials can still be supplied in each request as `api_key` and `api_secret`, matching the original application. `.env` values remain available as fallbacks.

HTTPS can be added later at Nginx/reverse-proxy level after the domain points to the VPS.
