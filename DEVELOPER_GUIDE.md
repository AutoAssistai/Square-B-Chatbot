# 👨‍💻 دليل المطورين - Square B Chatbot

## نظرة عامة على البنية

```
square-b-chatbot/
├── main.py                    # نقطة الدخول الرئيسية - FastAPI app
├── services/
│   ├── menu_service.py        # إدارة القائمة والبحث الذكي
│   └── chat_service.py        # الدردشة مع LLM
├── utils/
│   └── logger.py              # نظام التسجيل
├── static/
│   └── index.html             # واجهة المستخدم
├── logs/
│   └── chat.log               # سجلات التطبيق
├── MENU.txt                   # قائمة الطعام (مصدر البيانات)
├── requirements.txt           # المتطلبات
├── .env                       # متغيرات البيئة
└── test_chatbot.py           # اختبارات شاملة
```

---

## المكونات الأساسية

### 1. MenuService (`services/menu_service.py`)

**المسؤولية**: قراءة وتحليل وإدارة قائمة الطعام من `MENU.txt`

#### الميزات الرئيسية:

##### أ. تحليل MENU.txt
```python
async def load_menu(self) -> bool:
    """تحميل وتحليل القائمة من MENU.txt"""
```

يقرأ الملف ويستخرج:
- الفئات (BURGERS, SIDES, DRINKS, etc.)
- العناصر مع الأسعار
- الأحجام والخيارات (Regular, Meal)
- معلومات التوصيل

##### ب. البحث الذكي (Fuzzy Matching)
```python
def search_item(self, query: str, threshold: int = 60) -> List[Dict]:
    """البحث عن عنصر باستخدام RapidFuzz"""
```

**كيف يعمل**:
1. يستخدم `rapidfuzz` للمطابقة التقريبية
2. يبحث في:
   - أسماء العناصر
   - الأسماء العربية
   - Search aliases (المرادفات)
3. يعيد النتائج مرتبة حسب نسبة التطابق

**مثال**:
```python
# يبحث عن "شكن" (خطأ إملائي)
results = menu_service.search_item("شكن", threshold=60)
# يعيد: Chicken Burger (نسبة تطابق: 75%)
```

##### ج. Search Aliases

كل عنصر له مرادفات للبحث:
```python
search_aliases = [
    'دجاج', 'شكن', 'chicken', 'فراخ'  # لـ Chicken
    'بيف', 'لحم', 'لحمة', 'beef'      # لـ Beef
    'برجر', 'برقر', 'burger'           # عام
]
```

##### د. هيكل بيانات العنصر
```python
{
    'name': 'BEEF 1x1',                    # الاسم الأساسي
    'name_ar': 'BEEF 1x1',                 # الاسم بالعربي
    'category': 'BURGERS',                 # الفئة
    'subcategory': 'BEEF',                 # الفئة الفرعية
    'size': '1x1',                         # الحجم
    'price_regular': '3.50',               # السعر
    'price_regular_formatted': '3.50 دينار', # السعر منسق
    'type': 'regular',                     # النوع (regular/meal)
    'search_aliases': ['بيف', 'لحم', ...]  # المرادفات
}
```

---

### 2. ChatService (`services/chat_service.py`)

**المسؤولية**: التواصل مع LLM وتوليد الردود الذكية

#### الميزات الرئيسية:

##### أ. تحليل نوايا المستخدم
```python
def _analyze_intent(self, message: str) -> str:
    """يحدد نوع الطلب من رسالة المستخدم"""
```

**الأنواع المدعومة**:
1. `price_query`: السؤال عن الأسعار
2. `full_menu`: طلب القائمة كاملة
3. `suggestion`: طلب اقتراحات
4. `greeting`: تحية
5. `delivery`: الاستفسار عن التوصيل
6. `general`: أسئلة عامة

**كيف يعمل**:
```python
# يبحث عن كلمات مفتاحية
price_keywords = ['سعر', 'كم', 'بكم', 'price', 'قديش']
if any(keyword in message_lower for keyword in price_keywords):
    return 'price_query'
```

##### ب. بناء السياق
```python
def _build_context(self, intent: str, items: List[Dict]) -> str:
    """يبني السياق من عناصر القائمة لإرساله للـ LLM"""
```

**مثال على السياق**:
```
عناصر القائمة ذات الصلة:
  - BEEF 1x1 - 3.50 دينار
  - BEEF 2x2 - 4.75 دينار
  - BEEF 1x1 وجبة - 4.75 دينار
```

##### ج. System Prompt

يُبنى ديناميكياً حسب السياق:
```python
def _build_system_prompt(self, context: str) -> str:
    """ينشئ prompt للـ LLM مع القواعد والسياق"""
```

**القواعد المضمنة**:
- استخدم المعلومات من السياق فقط
- صيغة الأسعار: "X.XX دينار"
- الرد بالعربي الأردني دائماً
- اقتراحات ذكية ومختصرة

##### د. معاملات LLM المُحسّنة
```python
self.max_tokens = 500      # ردود مختصرة
self.temperature = 0.7     # توازن بين الإبداع والدقة
```

---

### 3. Main Application (`main.py`)

**المسؤولية**: FastAPI endpoints وإدارة الجلسات

#### Endpoints الرئيسية:

##### POST `/chat`
```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """نقطة الدردشة الرئيسية"""
```

**Flow**:
1. استلام الرسالة من المستخدم
2. إنشاء/استرجاع session
3. إضافة الرسالة لتاريخ الدردشة
4. توليد الرد من ChatService
5. حفظ الرد في session
6. الاحتفاظ بآخر 20 رسالة فقط

##### GET `/menu`
```python
@app.get("/menu")
async def get_menu():
    """عرض القائمة كاملة"""
```

##### POST `/menu/reload`
```python
@app.post("/menu/reload")
async def reload_menu():
    """إعادة تحميل القائمة من MENU.txt"""
```

##### GET `/health`
```python
@app.get("/health")
async def health_check():
    """فحص صحة التطبيق"""
```

---

## كيفية إضافة ميزات جديدة

### 1. إضافة Intent جديد

**في `chat_service.py`**:

```python
def _analyze_intent(self, message: str) -> str:
    # أضف intent جديد
    order_keywords = ['أطلب', 'أريد', 'بدي', 'order']
    if any(keyword in message_lower for keyword in order_keywords):
        return 'order_request'
    
    # ... باقي الكود
```

**ثم عدّل `_get_relevant_items`**:
```python
def _get_relevant_items(self, message: str, intent: str) -> List[Dict]:
    if intent == 'order_request':
        # منطق خاص بالطلبات
        return self._handle_order(message)
    
    # ... باقي الكود
```

### 2. إضافة فئة جديدة في القائمة

فقط أضفها في `MENU.txt` بنفس الصيغة:

```markdown
## 🍰 DESSERTS

- **Chocolate Cake** - 4.50 دينار
  كيك الشوكولاتة

- **Ice Cream** - 2.00 دينار
  آيس كريم
```

ستُضاف تلقائياً عند إعادة تحميل القائمة.

### 3. تحسين البحث

**في `menu_service.py`**:

```python
# أضف مرادفات جديدة
if 'dessert' in name_lower or 'حلو' in name_lower:
    search_aliases.extend(['حلويات', 'dessert', 'حلى'])
```

### 4. إضافة Endpoint جديد

**في `main.py`**:

```python
@app.post("/order")
async def place_order(order_items: List[str], session_id: str):
    """معالجة طلب جديد"""
    # منطق الطلب
    return {"order_id": "...", "status": "pending"}
```

### 5. تخزين بيانات إضافية

**استخدم Redis للتخزين الدائم**:

```python
import redis.asyncio as redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.post("/chat")
async def chat(request: ChatRequest):
    # احفظ في Redis بدلاً من الذاكرة
    await redis_client.setex(
        f"session:{session_id}", 
        3600,  # ساعة واحدة
        json.dumps(chat_history)
    )
```

---

## أفضل الممارسات

### 1. معالجة الأخطاء

**دائماً استخدم try-except**:
```python
try:
    result = await risky_operation()
except SpecificException as e:
    logger.error(f"Error: {str(e)}", exc_info=True)
    return fallback_response()
```

### 2. التسجيل (Logging)

```python
from utils.logger import setup_logger
logger = setup_logger()

# استخدم المستويات المناسبة
logger.info("✅ Operation successful")
logger.warning("⚠️ Warning message")
logger.error("❌ Error occurred", exc_info=True)
```

### 3. Type Hints

```python
from typing import List, Dict, Optional

def search_item(
    self, 
    query: str, 
    threshold: int = 60
) -> List[Dict]:
    """دائماً أضف type hints للوضوح"""
```

### 4. Async/Await

```python
# استخدم async للعمليات I/O
async def load_menu(self) -> bool:
    async with aiofiles.open(self.menu_file, 'r') as f:
        content = await f.read()
```

### 5. Validation

```python
from pydantic import BaseModel, validator

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    
    @validator('message')
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v
```

---

## الاختبار

### Unit Tests

```python
import pytest
from services.menu_service import MenuService

@pytest.mark.asyncio
async def test_menu_loading():
    menu_service = MenuService()
    success = await menu_service.load_menu()
    assert success
    assert len(menu_service.menu_items) > 0

@pytest.mark.asyncio
async def test_search_fuzzy_matching():
    menu_service = MenuService()
    await menu_service.load_menu()
    
    # اختبار خطأ إملائي
    results = menu_service.search_item("شكن")
    assert len(results) > 0
    assert "chicken" in results[0]['item']['name'].lower()
```

### Integration Tests

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat_endpoint():
    response = client.post(
        "/chat",
        json={"message": "كم سعر برجر بيف؟"}
    )
    assert response.status_code == 200
    assert "session_id" in response.json()
```

---

## الأداء والتحسين

### 1. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_category_items(self, category: str) -> List[Dict]:
    """Cache frequent queries"""
    return self.categories.get(category, [])
```

### 2. Async Operations

```python
# بدلاً من:
for item in items:
    process(item)

# استخدم:
tasks = [process_async(item) for item in items]
results = await asyncio.gather(*tasks)
```

### 3. Database Connection Pool

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,
    max_overflow=0
)
```

---

## الأمان

### 1. Input Validation

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = Field(None, regex=r'^session_[\d.]+$')
```

### 2. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_req: ChatRequest):
    # ...
```

### 3. API Key Protection

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
```

---

## المساهمة

### Git Workflow

```bash
# 1. أنشئ branch جديد
git checkout -b feature/new-feature

# 2. اعمل التغييرات
git add .
git commit -m "Add: new feature description"

# 3. Push
git push origin feature/new-feature

# 4. افتح Pull Request
```

### Commit Messages

```
Add: إضافة ميزة جديدة
Fix: إصلاح خطأ
Update: تحديث موجود
Refactor: إعادة هيكلة
Docs: تحديث التوثيق
Test: إضافة اختبارات
```

---

## موارد إضافية

- **FastAPI**: https://fastapi.tiangolo.com
- **OpenAI API**: https://platform.openai.com/docs
- **RapidFuzz**: https://github.com/maxbachmann/RapidFuzz
- **Pydantic**: https://docs.pydantic.dev

---

**Happy Coding! 🚀**
