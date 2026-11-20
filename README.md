# BitTiger Bybit P2P API — Docker Microservices

This repository packages the supplied Flask API into two isolated containers:

- `price-limit`: serves only `POST /api/ad-price-limit`
- `main-api`: serves all remaining API routes
- `nginx`: public reverse proxy; routes the price-limit path to its dedicated container

Both application containers use the same Docker image. The `SERVICE_ROLE` environment variable restricts which routes each container can serve.

## Requirements

- Fresh Ubuntu VPS (Ubuntu 24.04 recommended)
- Git

The bootstrap script installs Docker Engine and the Docker Compose plugin. No Python, pip packages, virtualenv, Nginx, or application dependencies need to be installed manually on the VPS. Docker builds the image and installs the pinned Python requirements.

## Local/VPS startup

```bash
# One-time VPS setup
sudo bash scripts/install-docker-ubuntu.sh

# Get the project
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY

# Configure optional fallback credentials
cp .env.example .env
nano .env

# Build and start all containers
bash scripts/deploy.sh
```

The public HTTP API is exposed through Nginx on port 80.

## Route mapping

| Public path | Container |
|---|---|
| `/api/ad-price-limit` | `bittiger-price-limit` |
| All other paths | `bittiger-main-api` |

## Test

```bash
curl http://127.0.0.1/health
```

The root and health paths are passed to the main API by Nginx. To inspect each container directly from the Docker network:

```bash
docker compose exec price-limit python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8090/health').read().decode())"
docker compose exec main-api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8090/health').read().decode())"
```

## Logs and operations

```bash
docker compose logs -f price-limit
docker compose logs -f main-api
docker compose logs -f nginx

docker compose restart price-limit
docker compose restart main-api
docker compose restart nginx

docker compose down
docker compose up -d --build
```

## Important notes

- The application currently accepts Bybit API credentials in request JSON bodies, matching the supplied source. `.env` credentials are only fallbacks.
- Do not commit `.env`. It is excluded by `.gitignore`/`.dockerignore` (add `.gitignore` before pushing).
- Nginx is initially configured for HTTP on port 80. HTTPS/Certbot should be configured after the domain points to the VPS.
- The price-limit cache is in-process memory. The Gunicorn worker count is intentionally one for that container so its cache and lock are shared by its request threads.
- The original Flask application logic is preserved; only container route isolation, health endpoint, and bind address were added.
# bittigerverse_bybit_api
