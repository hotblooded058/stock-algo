# Deployment Guide

## Quick Start (Docker)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
- AngelOne credentials in `config/secrets.py`

### Local Development

```bash
# Start both backend + frontend in Docker
./deployment/deploy.sh local

# Access:
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs

# View logs
./deployment/deploy.sh logs

# Stop
./deployment/deploy.sh stop

# Rebuild after code changes
./deployment/deploy.sh rebuild
```

### Production (VPS/Cloud)

1. **Get a VPS** (DigitalOcean $6/mo, AWS Lightsail $5/mo, any Linux server)

2. **Install Docker on server:**
```bash
curl -fsSL https://get.docker.com | sh
```

3. **Clone repo on server:**
```bash
git clone https://github.com/hotblooded058/stock-algo.git
cd stock-algo
```

4. **Set up secrets:**
```bash
cp deployment/.env.example deployment/.env
# Edit deployment/.env with your credentials

# Create secrets file
cat > config/secrets.py << 'EOF'
ANGELONE_API_KEY = "your_key"
ANGELONE_CLIENT_ID = "your_id"
ANGELONE_PASSWORD = "your_pin"
ANGELONE_TOTP_SECRET = "your_totp"
EOF
```

5. **Edit production config:**
```bash
# In deployment/docker-compose.prod.yml
# Change YOUR_SERVER_IP to your actual server IP
```

6. **Deploy:**
```bash
./deployment/deploy.sh prod
```

7. **Access:**
- Frontend: `http://YOUR_SERVER_IP:3000`
- API: `http://YOUR_SERVER_IP:8000/docs`

## Architecture

```
┌─────────────────────────────────────────┐
│              Docker Host                 │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │   Frontend   │  │    Backend       │ │
│  │   Next.js    │  │    FastAPI       │ │
│  │   :3000      │──│    :8000         │ │
│  └──────────────┘  └────────┬─────────┘ │
│                             │            │
│                    ┌────────┴─────────┐  │
│                    │  SQLite (volume) │  │
│                    │  trading.db      │  │
│                    └──────────────────┘  │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   Browser              AngelOne API
   (user)               (market data)
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile.backend` | Python backend image |
| `Dockerfile.frontend` | Next.js frontend image |
| `docker-compose.yml` | Local development |
| `docker-compose.prod.yml` | Production with resource limits |
| `nginx.conf` | Reverse proxy (optional, for SSL) |
| `deploy.sh` | One-command deployment script |
| `.env.example` | Environment variable template |

## Commands

| Command | What it does |
|---------|-------------|
| `./deployment/deploy.sh local` | Start locally |
| `./deployment/deploy.sh prod` | Start in production |
| `./deployment/deploy.sh stop` | Stop everything |
| `./deployment/deploy.sh logs` | View live logs |
| `./deployment/deploy.sh rebuild` | Rebuild after code changes |
| `./deployment/deploy.sh status` | Check container status |

## Database

SQLite database is stored in a Docker volume (`trading-data`).
It persists across container restarts and rebuilds.

To backup:
```bash
docker cp trading-backend:/app/data/trading.db ./backup-trading.db
```

To restore:
```bash
docker cp ./backup-trading.db trading-backend:/app/data/trading.db
```

## SSL (HTTPS)

For production with a domain name:

1. Get SSL certificate (Let's Encrypt):
```bash
apt install certbot
certbot certonly --standalone -d yourdomain.com
```

2. Copy certs to deployment/ssl/:
```bash
mkdir deployment/ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deployment/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem deployment/ssl/
```

3. Uncomment nginx service in `docker-compose.prod.yml`

4. Update `nginx.conf` with your domain

5. Rebuild: `./deployment/deploy.sh rebuild`

## Troubleshooting

**"Address already in use"**
```bash
# Kill existing processes on ports
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

**"Cannot connect to backend"**
```bash
# Check if backend is running
docker logs trading-backend

# Check health
curl http://localhost:8000/api/health
```

**"AngelOne login failed"**
- Check credentials in config/secrets.py
- TOTP secret may have changed — re-enable in AngelOne app
- IP address may have changed — update in AngelOne SmartAPI dashboard

**Database issues**
```bash
# Reset database (WARNING: deletes all data)
docker exec trading-backend rm /app/data/trading.db
docker restart trading-backend
```
