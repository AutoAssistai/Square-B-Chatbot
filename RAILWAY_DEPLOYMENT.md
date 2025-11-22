# 🚂 Railway.app Deployment Guide - Square B Chatbot

## Quick Deploy to Railway

### Method 1: Deploy from GitHub (Recommended)

#### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit - Square B Chatbot"
git branch -M main
git remote add origin https://github.com/yourusername/square-b-chatbot.git
git push -u origin main
```

#### Step 2: Deploy on Railway
1. Go to [Railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository
5. Railway will auto-detect and deploy!

#### Step 3: Set Environment Variables
In Railway Dashboard → Variables, add:
```
OPENAI_API_KEY=sk-your-api-key-here
MODEL=gpt-3.5-turbo
API_BASE_URL=https://openrouter.ai/api/v1
```

---

### Method 2: Deploy with Railway CLI

#### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

#### Step 2: Login
```bash
railway login
```

#### Step 3: Initialize Project
```bash
railway init
```

#### Step 4: Set Environment Variables
```bash
railway variables set OPENAI_API_KEY=sk-your-key
railway variables set MODEL=gpt-3.5-turbo
railway variables set API_BASE_URL=https://openrouter.ai/api/v1
```

#### Step 5: Deploy
```bash
railway up
```

---

## Environment Variables

### Required
- `OPENAI_API_KEY` - Your OpenAI or OpenRouter API key

### Optional
- `MODEL` - Model to use (default: gpt-3.5-turbo)
- `API_BASE_URL` - Custom API base URL (for OpenRouter)
- `PORT` - Port to run on (Railway sets this automatically)

---

## Configuration Files

Railway uses these files:

1. **railway.json** - Railway-specific configuration
2. **nixpacks.toml** - Nixpacks build configuration
3. **Procfile** - Process definitions
4. **requirements.txt** - Python dependencies

---

## After Deployment

### Get Your App URL
1. Go to Railway Dashboard
2. Click on your deployment
3. Go to **Settings** → **Domains**
4. You'll see your app URL: `https://your-app.railway.app`

### Custom Domain
1. In Railway Dashboard → Settings → Domains
2. Click **"Add Domain"**
3. Enter your custom domain
4. Configure DNS as instructed

---

## Monitoring

### View Logs
```bash
railway logs
```

Or in Railway Dashboard → Deployments → View Logs

### Check Health
```bash
curl https://your-app.railway.app/health
```

---

## Troubleshooting

### Build Failed
1. Check logs in Railway Dashboard
2. Verify `requirements.txt` is correct
3. Ensure Python 3.11 compatibility

### App Crashes
1. Check environment variables are set
2. Verify OPENAI_API_KEY is valid
3. Check logs for errors

### Port Issues
- Railway automatically sets `$PORT`
- Don't hardcode port in code
- Use `os.getenv("PORT", 8080)`

---

## Updating Your App

### Via GitHub
```bash
git add .
git commit -m "Update message"
git push
```
Railway auto-deploys on push!

### Via CLI
```bash
railway up
```

---

## Cost

Railway offers:
- **Free Tier**: $5 credit/month (no credit card required)
- **Developer Plan**: $5/month
- **Team Plan**: $20/month

Your app will likely fit in the free tier!

---

## Railway Dashboard

Access at: https://railway.app/dashboard

Features:
- Real-time logs
- Metrics & analytics
- Environment variables
- Deployments history
- Custom domains
- Database services

---

## Best Practices

1. ✅ Use environment variables for secrets
2. ✅ Enable auto-deploy from GitHub
3. ✅ Monitor logs regularly
4. ✅ Set up custom domain
5. ✅ Use health checks
6. ✅ Keep dependencies updated

---

## Support

- Railway Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Twitter: @Railway

---

## Security

⚠️ **NEVER** commit API keys to git!

✅ Use Railway environment variables
✅ Add `.env` to `.gitignore`
✅ Rotate keys regularly

---

Made with ❤️ for Square B
