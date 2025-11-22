# 🐳 Docker Deployment Guide - Square B Chatbot

## Quick Start

### 1. Using OpenAI

```bash
OPENAI_API_KEY="sk-your-openai-key" docker compose up --build -d
```

### 2. Using OpenRouter

```bash
OPENAI_API_KEY="sk-or-v1-your-key" \
API_BASE_URL="https://openrouter.ai/api/v1" \
MODEL="openai/gpt-3.5-turbo" \
docker compose up --build -d
```

### 3. Custom Port

```bash
OPENAI_API_KEY="your-key" \
PORT=8080 \
docker compose up --build -d
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | - | Your OpenAI or OpenRouter API key |
| `API_BASE_URL` | No | - | Custom API base URL (for OpenRouter) |
| `MODEL` | No | `gpt-3.5-turbo` | Model to use |
| `PORT` | No | `8080` | Port to expose |

---

## Commands

### Build and Start
```bash
OPENAI_API_KEY="your-key" docker compose up --build -d
```

### Stop
```bash
docker compose down
```

### View Logs
```bash
docker compose logs -f
```

### Restart
```bash
docker compose restart
```

### Remove Everything
```bash
docker compose down -v
```

---

## Access

- **Application**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

---

## Docker Files

- `Dockerfile`: Image definition
- `docker-compose.yml`: Service configuration
- `.dockerignore`: Files to exclude from build

---

## Troubleshooting

### Port Already in Use
```bash
# Use different port
PORT=8081 OPENAI_API_KEY="your-key" docker compose up --build -d
```

### Check Container Status
```bash
docker compose ps
```

### Check Container Logs
```bash
docker compose logs app
```

### Enter Container
```bash
docker compose exec app bash
```

### Rebuild from Scratch
```bash
docker compose down -v
docker compose build --no-cache
OPENAI_API_KEY="your-key" docker compose up -d
```

---

## Production Deployment

### With Environment File

Create `.env` file:
```env
OPENAI_API_KEY=your-key
API_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-3.5-turbo
PORT=8080
```

Then run:
```bash
docker compose up --build -d
```

### Behind Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Security Notes

⚠️ **NEVER** commit API keys to git!

✅ Use environment variables
✅ Add `.env` to `.gitignore`
✅ Use secrets management in production
✅ Rotate keys regularly

---

## Health Check

The container includes automatic health checks:
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

Check health:
```bash
docker compose ps
```

---

## Logs

Logs are mounted to `./logs` directory on host.

View logs:
```bash
# Docker logs
docker compose logs -f

# Application logs
tail -f logs/chat.log
```

---

## Updates

Update to latest code:
```bash
git pull
docker compose up --build -d
```

---

## Clean Up

Remove containers and volumes:
```bash
docker compose down -v
```

Remove images:
```bash
docker rmi square-b-chatbot:latest
```

---

Made with ❤️ for Square B
