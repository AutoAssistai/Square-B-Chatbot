# 🚀 دليل النشر والتشغيل - Square B Chatbot

## المتطلبات الأساسية

### 1. البيئة التقنية
- Python 3.8 أو أحدث
- pip (مدير حزم Python)
- 512 MB RAM على الأقل
- اتصال بالإنترنت

### 2. API Key
يحتاج التطبيق إلى API key من أحد المزودين:
- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **OpenRouter** (يدعم عدة نماذج)
- أي مزود متوافق مع OpenAI API

---

## التثبيت السريع

### الطريقة الأولى: باستخدام السكريبت (Linux/Mac)

```bash
# 1. امنح صلاحيات التنفيذ
chmod +x start.sh

# 2. شغّل التطبيق
./start.sh
```

### الطريقة الثانية: يدوياً

```bash
# 1. أنشئ بيئة افتراضية
python3 -m venv venv

# 2. فعّل البيئة الافتراضية
# على Linux/Mac:
source venv/bin/activate
# على Windows:
venv\Scripts\activate

# 3. ثبّت المتطلبات
pip install -r requirements.txt

# 4. شغّل التطبيق
python main.py
```

---

## إعداد البيئة (.env)

أنشئ أو عدّل ملف `.env` في المجلد الرئيسي:

```env
# === LLM Configuration ===
# استخدم OpenAI مباشرة
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4

# أو استخدم OpenRouter
# API_KEY=your-openrouter-key
# API_BASE_URL=https://openrouter.ai/api/v1
# MODEL=openai/gpt-4

# === Menu Configuration ===
MENU_TXT=MENU.txt

# === Logging ===
LOG_FILE=logs/chat.log

# === Server ===
PORT=8000
```

### الحصول على API Keys

#### OpenAI
1. سجّل في: https://platform.openai.com
2. اذهب إلى API Keys
3. أنشئ key جديد
4. انسخه في `.env` تحت `OPENAI_API_KEY`

#### OpenRouter (بديل مجاني للتجربة)
1. سجّل في: https://openrouter.ai
2. احصل على API key مجاني
3. أضفه في `.env`:
   ```env
   API_KEY=sk-or-v1-xxxxx
   API_BASE_URL=https://openrouter.ai/api/v1
   MODEL=openai/gpt-3.5-turbo
   ```

---

## التشغيل

### Development Mode (تطوير)

```bash
# طريقة 1: باستخدام السكريبت
./start.sh

# طريقة 2: مباشرة
python main.py

# طريقة 3: باستخدام uvicorn مع hot reload
uvicorn main:app --reload --port 8000
```

سيعمل التطبيق على:
- **الواجهة**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Production Mode (إنتاج)

```bash
# باستخدام Gunicorn (أفضل للإنتاج)
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# أو باستخدام uvicorn مباشرة
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## الاختبار

### 1. اختبار خدمة القائمة فقط (لا يحتاج API key)

```bash
python test_chatbot.py
```

### 2. اختبار API endpoints

```bash
# تأكد من تشغيل الخادم أولاً في terminal منفصل
python main.py

# ثم في terminal آخر:
python example_usage.py specific
```

### 3. اختبار يدوي

```bash
# Health check
curl http://localhost:8000/health

# عرض القائمة
curl http://localhost:8000/menu

# اختبار دردشة
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "كم سعر برجر بيف؟"}'
```

---

## النشر على خادم

### Docker

أنشئ ملف `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

بناء وتشغيل:

```bash
# بناء الصورة
docker build -t square-b-chatbot .

# تشغيل الحاوية
docker run -d -p 8000:8000 --env-file .env square-b-chatbot
```

### Docker Compose

أنشئ ملف `docker-compose.yml`:

```yaml
version: '3.8'

services:
  chatbot:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./MENU.txt:/app/MENU.txt
    restart: unless-stopped
```

التشغيل:

```bash
docker-compose up -d
```

### VPS/Cloud (Ubuntu/Debian)

```bash
# 1. حدّث النظام
sudo apt update && sudo apt upgrade -y

# 2. ثبّت Python و pip
sudo apt install python3 python3-pip python3-venv -y

# 3. انسخ المشروع
git clone <your-repo-url>
cd square-b-chatbot

# 4. أنشئ البيئة الافتراضية
python3 -m venv venv
source venv/bin/activate

# 5. ثبّت المتطلبات
pip install -r requirements.txt

# 6. أعد ملف .env
nano .env
# (أضف API keys هنا)

# 7. ثبّت كخدمة systemd
sudo nano /etc/systemd/system/square-b-chatbot.service
```

محتوى الخدمة:

```ini
[Unit]
Description=Square B Chatbot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/square-b-chatbot
Environment="PATH=/path/to/square-b-chatbot/venv/bin"
ExecStart=/path/to/square-b-chatbot/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

تفعيل الخدمة:

```bash
sudo systemctl daemon-reload
sudo systemctl enable square-b-chatbot
sudo systemctl start square-b-chatbot
sudo systemctl status square-b-chatbot
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## المراقبة والصيانة

### عرض السجلات

```bash
# سجلات التطبيق
tail -f logs/chat.log

# سجلات systemd (إذا استخدمت systemd)
sudo journalctl -u square-b-chatbot -f
```

### إعادة تحميل القائمة

```bash
curl -X POST http://localhost:8000/menu/reload
```

### مسح جلسة

```bash
curl -X DELETE http://localhost:8000/session/SESSION_ID
```

---

## استكشاف الأخطاء

### المشكلة: "Menu file not found"
**الحل**: تأكد من وجود ملف `MENU.txt` في نفس المجلد

### المشكلة: "Invalid API Key"
**الحل**: 
1. تأكد من صحة API key في `.env`
2. تحقق من رصيد API (إذا كان OpenAI)
3. جرّب OpenRouter كبديل

### المشكلة: "Port already in use"
**الحل**:
```bash
# ابحث عن العملية
lsof -i :8000

# أوقف العملية
kill -9 <PID>

# أو غيّر المنفذ في .env
PORT=8001
```

### المشكلة: استجابات بطيئة
**الحل**:
1. قلل `max_tokens` في `chat_service.py`
2. استخدم نموذج أسرع (gpt-3.5-turbo بدلاً من gpt-4)
3. زد عدد workers في gunicorn

### المشكلة: استهلاك ذاكرة عالي
**الحل**:
1. تأكد من أن `MAX_SESSION_MESSAGES = 20` في `main.py`
2. استخدم Redis لتخزين الجلسات (في الإنتاج)
3. قم بمسح الجلسات القديمة دورياً

---

## الأمان

### إنتاج Production:

1. **HTTPS فقط**: استخدم SSL certificate
   ```bash
   # مع Let's Encrypt
   sudo certbot --nginx -d your-domain.com
   ```

2. **قيود CORS**: عدّل في `main.py`
   ```python
   allow_origins=["https://your-domain.com"]
   ```

3. **Rate Limiting**: أضف rate limiter
   ```bash
   pip install slowapi
   ```

4. **Environment Variables**: لا ترفع `.env` إلى Git
   ```bash
   # تأكد من وجوده في .gitignore
   echo ".env" >> .gitignore
   ```

5. **Firewall**: افتح المنافذ الضرورية فقط
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

---

## الأداء والتحسين

### Redis للجلسات (اختياري)

```bash
pip install redis aioredis

# في main.py بدّل:
# sessions = {}  # In-memory
# بـ:
# import redis.asyncio as redis
# redis_client = redis.Redis(host='localhost', port=6379)
```

### Caching

أضف caching للردود المتكررة:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_popular_items():
    # ...
```

---

## الدعم

- 📧 البريد: support@square-b.com
- 📱 الهاتف: 0797920111
- 🌐 الموقع: https://square-b.com

---

## الترخيص

هذا المشروع مفتوح المصدر ومتاح للاستخدام التجاري والشخصي.

---

**صُنع بـ ❤️ لمطعم Square B**
