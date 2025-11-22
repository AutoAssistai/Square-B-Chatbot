# main.py
# Demo Arabic Chatbot for "Square B" restaurant using FastAPI
# This app serves a simple rule-based chatbot with a lightweight web UI.
# It loads menu data from a JSON/CSV file and can respond to basic queries.

from fastapi import FastAPI, Request, HTTPException, Cookie
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
import os
import json
import csv
import uuid
import re
from datetime import datetime

# PDF/OCR dependencies
try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None  # type: ignore

try:
    import pytesseract  # type: ignore
    from PIL import Image, ImageEnhance, ImageFilter  # type: ignore
except Exception:
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

# pdf2image for converting PDF pages to images (requires poppler on system)
try:
    from pdf2image import convert_from_path  # type: ignore
except Exception:
    convert_from_path = None  # type: ignore

# Optional OpenAI client (LLM). If not configured, we fallback to rule-based.
OPENAI_AVAILABLE = False
try:
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # dotenv is optional; the app will still run with defaults
    pass

# ----- Configuration -----
PROJECT_NAME = os.getenv("PROJECT_NAME", "Square B - Arabic Chatbot Demo")
MENU_FILE = os.getenv("MENU_FILE", "data/menu.json")
MENU_TXT = os.getenv("MENU_TXT", os.getenv("TXT_FILE", "MENU.txt"))
# Support both legacy and requested env names
MENU_PDF = os.getenv("MENU_PDF", os.getenv("PDF_FILE", ""))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("API_KEY", ""))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("MODEL", "gpt-4o-mini"))
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", os.getenv("API_BASE_URL", ""))
MENU_CACHE = os.getenv("MENU_CACHE", "data/menu_cache.json")
LOG_FILE = os.getenv("LOG_FILE", "logs/chat.log")

# ----- App Setup -----
app = FastAPI(title=PROJECT_NAME)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ----- Data Models -----
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class MenuItem(BaseModel):
    id: str
    name: str
    color: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None

# ----- In-Memory State (for demo only) -----
MENU: List[MenuItem] = []
MENU_SOURCE_PATH: Optional[str] = None
MENU_MTIME: Optional[float] = None
# Simple in-memory chat history store: {session_id: [(role, content), ...]}
CHAT_HISTORY: Dict[str, List[Tuple[str, str]]] = {}  # capped to ~20 messages

# ----- Helpers -----
def load_menu_from_txt(txt_path: str) -> List[MenuItem]:
    items: List[MenuItem] = []
    if not os.path.exists(txt_path):
        return items
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]

    current_category: Optional[str] = None
    current_sub: Optional[str] = None
    pending_desc: Optional[str] = None
    in_table: bool = False

    price_num = lambda s: float(s.replace('JD', '').strip()) if s else None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Category and subcategory headers
        if line.startswith('## '):
            current_category = line[3:].strip(' #')
            current_sub = None
            pending_desc = None
            in_table = False
            i += 1
            continue
        if line.startswith('### '):
            current_sub = line[4:].strip()
            pending_desc = None
            in_table = False
            i += 1
            continue

        # Subcategory descriptions (bold english then arabic)
        if line.startswith('**') and line.endswith('**') and len(line) > 4:
            # bold description line
            desc_en = line.strip('* ')
            # lookahead for arabic description on next line if present
            next_line = lines[i+1].strip() if i+1 < len(lines) else ''
            desc = desc_en
            if next_line and not next_line.startswith('|') and not next_line.startswith('**') and not next_line.startswith('##') and not next_line.startswith('###'):
                desc = f"{desc_en} / {next_line}"
                i += 1
            pending_desc = desc
            i += 1
            continue

        # Burgers tables (Size | Regular | Meal)
        if '| Size |' in line and 'Regular' in line and 'Meal' in line:
            in_table = True
            i += 2  # skip header separator
            while i < len(lines):
                row = lines[i].strip()
                if not row or not row.startswith('|'):
                    break
                cols = [c.strip() for c in row.strip('|').split('|')]
                if len(cols) >= 3:
                    size = cols[0]
                    try:
                        price_reg = price_num(cols[1].replace('JD', '').strip())
                    except Exception:
                        price_reg = None
                    try:
                        price_meal = price_num(cols[2].replace('JD', '').strip())
                    except Exception:
                        price_meal = None
                    base_name = (current_sub or 'BURGER').strip()
                    cat = 'BURGERS'
                    if price_reg is not None:
                        items.append(MenuItem(
                            id=f"{base_name}-{size}-regular",
                            name=f"{base_name} {size} (Regular)",
                            price=price_reg,
                            category=cat,
                            description=pending_desc
                        ))
                    if price_meal is not None:
                        items.append(MenuItem(
                            id=f"{base_name}-{size}-meal",
                            name=f"{base_name} {size} (Meal)",
                            price=price_meal,
                            category=cat,
                            description=pending_desc
                        ))
                i += 1
            continue

        # Bulleted items like Kids, Sides, Drinks with optional arabic description in next line
        m = re.match(r"^- \*\*(.+?)\*\* - ([0-9.]+) JD\s*$", line)
        if m:
            name = m.group(1).strip()
            price = None
            try:
                price = float(m.group(2))
            except Exception:
                price = None
            # Optional next line description (arabic)
            desc_line = lines[i+1].strip() if i+1 < len(lines) else ''
            desc = desc_line if desc_line and not desc_line.startswith('-') and not desc_line.startswith('**') and not desc_line.startswith('|') else None
            cat_map = {
                'KIDS MENU': 'KIDS',
                'SIDES': 'SIDES',
                'DRINKS': 'DRINKS'
            }
            cat = cat_map.get((current_category or '').upper(), current_category)
            items.append(MenuItem(
                id=f"{name}".lower().replace(' ', '-'),
                name=name.title() if name.isupper() else name,
                price=price,
                category=cat,
                description=desc
            ))
            if desc is not None:
                i += 1
            i += 1
            continue

        # Sauces block: price in header then list
        if (current_category or '').upper().startswith('🧂 SAUCES') or (current_category or '').upper() == 'SAUCES':
            # Detect per-line sauces names with a static price if stated above
            if '0.50 JD' in line:
                pending_desc = 'Each sauce 0.50 JD'
                i += 1
                continue
            if line.startswith('- '):
                sauce_name = line[2:].strip()
                items.append(MenuItem(
                    id=f"sauce-{sauce_name}".lower().replace(' ', '-'),
                    name=sauce_name,
                    price=0.50,
                    category='SAUCES',
                    description=pending_desc
                ))
                i += 1
                continue

        i += 1

    return items


def find_pdf_menu_path() -> Optional[str]:
    # Priority: MENU_PDF env, then MENU_FILE if pdf, else search workspace for *.pdf
    candidates: List[str] = []
    if MENU_PDF:
        candidates.append(MENU_PDF)
    if MENU_FILE and os.path.splitext(MENU_FILE)[1].lower() == ".pdf":
        candidates.append(MENU_FILE)
    # search common names
    for fname in os.listdir('.'):
        if fname.lower().endswith('.pdf'):
            candidates.append(fname)
    for path in candidates:
        if os.path.exists(path):
            return path
    return None
    # Priority: MENU_PDF env, then MENU_FILE if pdf, else search workspace for *.pdf
    candidates: List[str] = []
    if MENU_PDF:
        candidates.append(MENU_PDF)
    if MENU_FILE and os.path.splitext(MENU_FILE)[1].lower() == ".pdf":
        candidates.append(MENU_FILE)
    # search common names
    for fname in os.listdir('.'):
        if fname.lower().endswith('.pdf'):
            candidates.append(fname)
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def preprocess_image(im: Image.Image) -> Image.Image:
    # Convert to grayscale
    gray = im.convert('L')
    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    high_contrast = enhancer.enhance(1.8)
    # Reduce noise
    denoised = high_contrast.filter(ImageFilter.MedianFilter(size=3))
    # Adaptive-ish threshold via point function
    bw = denoised.point(lambda x: 0 if x < 160 else 255, mode='1')
    return bw.convert('L')


def ocr_pdf_with_images(pdf_path: str, dpi: int = 300) -> str:
    """Use pdf2image to convert pages to images and run Arabic OCR with Tesseract.
    Applies preprocessing pipeline to improve accuracy."""
    if convert_from_path is None or pytesseract is None:
        return ""
    try:
        pages = convert_from_path(pdf_path, dpi=dpi)
    except Exception:
        return ""
    ocr_texts: List[str] = []
    for im in pages:
        try:
            # Try multiple variants to maximize recall
            variants = [im, preprocess_image(im)]
            page_texts = []
            for v in variants:
                txt = pytesseract.image_to_string(v, lang='ara')
                if txt and txt.strip():
                    page_texts.append(txt)
            if page_texts:
                ocr_texts.append("\n".join(page_texts))
        except Exception:
            continue
    return "\n".join(ocr_texts)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF; prefer embedded text via pdfplumber, fallback to pdf2image+OCR (Arabic)."""
    combined: List[str] = []
    text_len = 0

    # First try pdfplumber for embedded text
    if pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                    if t.strip():
                        combined.append(t)
                        text_len += len(t)
        except Exception:
            pass

    # If not enough text, use OCR via pdf2image
    if text_len < 50:  # threshold; assumes minimal content
        ocr_txt = ocr_pdf_with_images(pdf_path, dpi=300)
        if ocr_txt:
            combined.append(ocr_txt)

    return "\n".join([c for c in combined if c and c.strip()])


def parse_menu_lines_to_items(lines: List[str]) -> List[MenuItem]:
    """Parse menu lines into MenuItem objects using heuristics for Arabic names, prices, categories, and inline descriptions."""
    items: List[MenuItem] = []
    price_regex = re.compile(r"(?:(\d+[\.,]?\d*)\s*(?:ر\.?س|SAR|ر.?س|ريال))|(?:سعر\s*(\d+[\.,]?\d*))")
    arabic_re = re.compile(r"[\u0600-\u06FF]")
    # Common separators that might divide name/description
    sep_regex = re.compile(r"\s[-–—:\|]\s|")

    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if not arabic_re.search(line):
            continue
        # Extract price
        price_match = price_regex.search(line)
        price_val: Optional[float] = None
        if price_match:
            val = next((v for v in price_match.groups() if v), None)
            if val:
                try:
                    price_val = float(val.replace(',', '.'))
                except Exception:
                    price_val = None
        # Remove price tokens from text
        text_wo_price = price_regex.sub('', line).strip(" -–—:|\t")

        # Split into possible name and description using separators
        name_part = text_wo_price
        desc_part = None
        for sep in [' - ', ' – ', ' — ', ' | ', ': ']:
            if sep in text_wo_price:
                parts = [p.strip() for p in text_wo_price.split(sep, 1)]
                if len(parts) == 2:
                    name_part, desc_part = parts[0], parts[1]
                    break
        # Detect category cues
        category = None
        for cat in ["مشروبات", "حلويات", "سلطات", "سندويتشات", "مقبلات", "برجر", "قهوة"]:
            if cat in line:
                category = cat
                break
        if len(name_part) < 2:
            continue
        items.append(MenuItem(id=f"pdf-{idx}", name=name_part, price=price_val, category=category, description=desc_part))

    # Deduplicate by name keeping first with price/description
    seen: Dict[str, MenuItem] = {}
    for it in items:
        key = it.name
        if key not in seen:
            seen[key] = it
        else:
            cur = seen[key]
            if cur.price is None and it.price is not None:
                cur.price = it.price
            if (not cur.description) and it.description:
                cur.description = it.description
            if (not cur.category) and it.category:
                cur.category = it.category
    return list(seen.values())


def load_menu_cache(src_path: str) -> Optional[List[MenuItem]]:
    try:
        if not MENU_CACHE or not os.path.exists(MENU_CACHE):
            return None
        with open(MENU_CACHE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        meta = data.get('meta') or {}
        if meta.get('source_path') != src_path:
            return None
        src_mtime = os.path.getmtime(src_path)
        if meta.get('source_mtime') != src_mtime:
            return None
        items_raw = data.get('items') or []
        return [MenuItem(**it) for it in items_raw]
    except Exception:
        return None


def save_menu_cache(src_path: str, items: List[MenuItem]) -> None:
    try:
        os.makedirs(os.path.dirname(MENU_CACHE), exist_ok=True)
        payload = {
            'meta': {
                'source_path': src_path,
                'source_mtime': os.path.getmtime(src_path),
                'cached_at': datetime.utcnow().isoformat() + 'Z'
            },
            'items': [it.model_dump() for it in items]
        }
        with open(MENU_CACHE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_menu(menu_path: str) -> List[MenuItem]:
    """Load menu from JSON, CSV, or PDF dynamically."""
    # If explicit path missing, try finding PDF automatically
    if not menu_path or not os.path.exists(menu_path):
        pdf_auto = find_pdf_menu_path()
        if pdf_auto:
            menu_path = pdf_auto
        else:
            return []

    ext = os.path.splitext(menu_path)[1].lower()
    items: List[MenuItem] = []
    try:
        if ext == ".json":
            with open(menu_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for row in data:
                    items.append(MenuItem(**row))
        elif ext == ".csv":
            with open(menu_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    price_val: Optional[float] = None
                    if row.get("price") not in (None, ""):
                        try:
                            price_val = float(str(row.get("price")).replace(",", "."))
                        except ValueError:
                            price_val = None
                    items.append(MenuItem(
                        id=str(row.get("id", "")) or f"csv-{len(items)+1}",
                        name=str(row.get("name", "")).strip(),
                        color=(row.get("color") or None),
                        price=price_val,
                        category=(row.get("category") or None),
                        description=(row.get("description") or None),
                    ))
        elif ext == ".pdf":
            # Try cache first
            cache_items = load_menu_cache(menu_path)
            if cache_items is not None:
                items = cache_items
            else:
                text = extract_text_from_pdf(menu_path)
                lines = [l for part in text.split('\n') for l in [part] if l.strip()]
                items = parse_menu_lines_to_items(lines)
                save_menu_cache(menu_path, items)
        else:
            return []
    except Exception:
        return []
    return items


def fmt_jd(price: Optional[float]) -> str:
    return f"{price:.2f} دينار" if price is not None else ""


def format_menu_item(item: MenuItem) -> str:
    parts = [f"• {item.name}"]
    if item.color:
        parts.append(f"اللون: {item.color}")
    if item.price is not None:
        parts.append(f"السعر: {fmt_jd(item.price)}")
    if item.category:
        parts.append(f"القسم: {item.category}")
    return " | ".join(parts)


def product_image_url(item: MenuItem) -> str:
    # Try to use local static image by id, fallback to placeholder
    img_path = f"/static/images/{item.id}.svg"
    # In a real app we would check file existence; for demo, always serve path and let frontend fallback CSS handle it
    return img_path


def find_menu_items_by_keyword(keyword: str) -> List[MenuItem]:
    k = keyword.strip().lower()
    results: List[MenuItem] = []
    for item in MENU:
        # Search by name, color, category, description
        name = (item.name or "").lower()
        color = (item.color or "").lower()
        category = (item.category or "").lower()
        desc = (item.description or "").lower()
        if k in name or k in color or k in category or k in desc:
            results.append(item)
    return results


# ----- Simple Rule-based Bot -----
def generate_demo_response(user_text: str) -> str:
    """Smart Arabic (Jordanian) fallback based on MENU.txt only, with fuzzy matching and intents."""
    text = normalize(user_text)

    def join_prices(items: List[MenuItem], limit: int = 6) -> str:
        out = []
        for it in items[:limit]:
            price = fmt_jd(it.price) if it.price is not None else ""
            out.append(f"- {it.name}: {price}")
        return "\n".join(out) if out else ""

    # Common intents
    greet_kw = ["مرحبا", "هلا", "سلام", "صباح", "مساء"]
    price_kw = ["سعر", "كم", "قديش", "بكم", "price", "much", "cost"]
    menu_kw = ["منيو", "القائمة", "menu", "الأصناف", "المنيو"]
    suggest_kw = ["ترشح", "تنصح", "اقتراح", "شو بتنصحني", "وش ترشح", "recommend"]

    if any(k in text for k in greet_kw):
        return "أهلاً في Square B! شو نفسك تجربه اليوم؟ بدك أقترحلك على حسب المزاج؟"

    if any(k in text for k in ["ساعات", "الدوام", "مواعيد", "متى", "وينكم", "الموقع", "الدفع", "بطاقة", "فيزا", "ماستر"]):
        if any(k in text for k in ["وين", "الموقع", "address", "فرع"]):
            return "موقعنا بالتوصيل، وبتلاقي رقم الدليفري عالمنيو: 0797920111. بتحب أرتبلك طلب؟"
        if any(k in text for k in ["ساعات", "الدوام", "متى"]):
            return "بنخدمك يومياً من 10 الصبح لـ 11 بالليل تقريباً. بتحب نجهزلك طلب؟"
        if any(k in text for k in ["الدفع", "بطاقة", "فيزا", "ماستر"]):
            return "ندعم كاش وبطاقات حسب مزوّد التوصيل. بتحب تدفع كاش أو بطاقة؟"

    # Show menu
    if any(k in text for k in menu_kw):
        if not MENU:
            return "للأسف ما لقيت المنيو حالياً. جرّب تعيد التشغيل."
        cats = {}
        for it in MENU:
            cats.setdefault(it.category or "", 0)
            cats[it.category or ""] += 1
        top = [c for c,_ in sorted(cats.items(), key=lambda x: x[1], reverse=True)][:3]
        preview = join_prices(MENU, limit=10)
        return f"أكيد! عندنا أقسام: {', '.join([c for c in top if c])}. بعض الأصناف:\n{preview}\nتحب أفرزلك حسب القسم؟"

    # Price intent
    if any(k in text for k in price_kw):
        matched = find_items_in_text(text)
        if matched:
            it = matched[0]
            price = fmt_jd(it.price) if it.price is not None else "غير محدد"
            upsell = [m for m in MENU if m.category == it.category and m.id != it.id][:1]
            ups = f" وجنبها {upsell[0].name}؟" if upsell else ""
            return f"سعر {it.name} {price}.{ups} بتحب أضيفه لإلك؟"
        # No match
        return "آسف، مش قادر ألاقي الصنف المطلوب. سمّيلِي الاسم بدقة شوي لو سمحت."

    # Suggest intent
    if any(k in text for k in suggest_kw):
        if not MENU:
            return "المنيو مش ظاهر عندي هسه. جرّب كمان مرة."
        # Simple heuristic: pick 1 burger + 1 side + 1 drink if available
        burgers = [m for m in MENU if (m.category or '').upper().startswith('BURGER') or (m.category or '').upper()=='BURGERS']
        sides = [m for m in MENU if (m.category or '').upper().startswith('SIDE')]
        drinks = [m for m in MENU if (m.category or '').upper().startswith('DRINK')]
        picks = []
        if burgers: picks.append(burgers[0])
        if sides: picks.append(sides[0])
        if drinks: picks.append(drinks[0])
        if picks:
            lines = join_prices(picks, limit=3)
            return f"بنصحك بهدول:\n{lines}\nبدك أضيفهم لإلك؟"
        return "بنصحك نجرب برغر مع سايد خفيفة ومشروب. بتحب أختارلك؟"

    # Try fuzzy match general info
    matched = find_items_in_text(text)
    if matched:
        lines = join_prices(matched, limit=5)
        return f"لقيت هدول الأقرب لسؤالك:\n{lines}\nتحب أضيف واحد منهم لإلك؟"

    # Outside menu
    return "آسف، مش قادر ألاقي هالصنف بالمنيو، ممكن تسألني عن شي تاني من قائمتنا؟"


# ----- Product Suggestions -----
def suggest_products(user_text: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """Simple heuristic suggestions based on keywords and categories for upsell/cross-sell."""
    if not MENU:
        return []
    text = (user_text or "").lower()

    # Keyword signals
    wants_sweet = any(k in text for k in ["حلى", "حلا", "حلويات", "كيك", "شوكولاتة", "dessert"])
    wants_drink = any(k in text for k in ["عصير", "مشروب", "مشروبات", "قهوة", "لاتيه", "drink", "قهوه"])
    wants_light = any(k in text for k in ["خفيف", "لايت", "سلطة", "سلطات", "healthy"])

    def pick(cat: str) -> List[MenuItem]:
        return [m for m in MENU if (m.category or '').lower() == cat]

    pool: List[MenuItem] = []
    if wants_sweet:
        pool += pick("حلويات")
    if wants_drink:
        pool += pick("مشروبات")
    if wants_light:
        pool += pick("سلطات")

    # If no signals, do a simple cross-sell mix: 1 drink, 1 dessert, 1 other
    if not pool:
        pool += (pick("مشروبات")[:2] + pick("حلويات")[:2] + MENU[:2])

    # Deduplicate while preserving order
    seen = set()
    unique_pool = []
    for m in pool:
        if m.id not in seen:
            unique_pool.append(m)
            seen.add(m.id)

    suggestions = []
    for item in unique_pool[:top_n]:
        suggestions.append({
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "image": product_image_url(item)
        })
    return suggestions


# ----- LLM Integration -----
def build_system_prompt() -> str:
    return (
        "أنت خبير خدمة عملاء افتراضي لمطعم Square B. رد باللهجة الأردنية وباختصار، وكون واضح وودود. "
        "اعتمد حصراً على بيانات المنيو (MENU.txt). لا تخترع معلومات. "
        "اذكر الأسعار دائماً بالدينار الأردني فقط وبدون أي تحويل عملات، مثلاً: 6.75 دينار أو 4.50 JD. "
        "لو السؤال بغير العربي، افهمه ورد بالعربي الأردني. "
        "قدّم اقتراحات Upsell/Cross-sell مناسبة حسب نفس الفئة أو سعر قريب، واختم بسؤال قصير للتفاعل."
    )


def menu_to_context() -> str:
    if not MENU:
        return "لا توجد بيانات منيو حالياً."
    lines = []
    for m in MENU[:100]:
        parts = [m.name]
        if m.category:
            parts.append(f"({m.category})")
        if m.price is not None:
            parts.append(f"{fmt_jd(m.price)}")
        if m.color:
            parts.append(f"لون: {m.color}")
        if m.description:
            parts.append(f"وصف: {m.description}")
        lines.append(" - "+" | ".join(parts))
    return "\n".join(lines)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or '').strip()).lower()


import difflib

def find_items_in_text(user_text: str) -> List[MenuItem]:
    if not MENU:
        return []
    text = normalize(user_text)
    # Direct matches
    direct = [it for it in MENU if normalize(it.name or '') and normalize(it.name or '') in text]
    if direct:
        return direct[:5]
    # Fuzzy matches for typos and mixed languages
    names = [normalize(it.name or '') for it in MENU]
    tokens = [w for w in re.split(r"\W+", text) if len(w) >= 3]
    scored: List[Tuple[float, MenuItem]] = []
    for it in MENU:
        nm = normalize(it.name or '')
        score = max([difflib.SequenceMatcher(a=nm, b=tk).ratio() for tk in tokens] or [0.0])
        if score >= 0.6:
            scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:5]]


def chat_with_llm(session_id: str, user_text: str) -> str:
    # Fallback to rules if no OpenAI
    if not (OPENAI_AVAILABLE and OPENAI_API_KEY):
        return generate_demo_response(user_text)

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)

    # Prepare history
    history = CHAT_HISTORY.get(session_id, [])[-20:]
    messages = [{"role": "system", "content": build_system_prompt()},
                {"role": "system", "content": "ملخص المنيو (من MENU.txt):\n" + menu_to_context()}]
    matched = find_items_in_text(user_text)
    if matched:
        lines = []
        for m in matched:
            parts = [m.name]
            if m.price is not None:
                parts.append(fmt_jd(m.price))
            if m.category:
                parts.append(f"({m.category})")
            if m.description:
                parts.append(f"وصف: {m.description}")
            lines.append(" - "+" | ".join(parts))
        messages.append({"role": "system", "content": "عناصر مُطابقة لرسالة العميل:\n" + "\n".join(lines)})
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text})

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=220,
        )
        reply = completion.choices[0].message.content.strip()
        return reply
    except Exception:
        return generate_demo_response(user_text)


# ----- Routes -----
@app.get("/")
async def home(request: Request):
    # Render the chat UI
    return templates.TemplateResponse("index.html", {"request": request, "project_name": PROJECT_NAME})


def refresh_menu_if_needed():
    global MENU, MENU_SOURCE_PATH, MENU_MTIME
    # Enforce TXT-only policy
    if MENU_TXT and os.path.exists(MENU_TXT):
        mtime = os.path.getmtime(MENU_TXT)
        if MENU_SOURCE_PATH != MENU_TXT or MENU_MTIME != mtime or not MENU:
            MENU = load_menu_from_txt(MENU_TXT)
            MENU_SOURCE_PATH = MENU_TXT
            MENU_MTIME = mtime
    else:
        # No TXT found: clear menu to avoid stale data
        MENU = []
        MENU_SOURCE_PATH = MENU_TXT
        MENU_MTIME = None


@app.get("/menu")
async def get_menu(q: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None):
    # Ensure latest menu from PDF/JSON/CSV
    refresh_menu_if_needed()
    items = MENU
    if q:
        ql = q.lower()
        items = [i for i in items if ql in (i.name or '').lower() or ql in (i.category or '').lower() or ql in (i.description or '').lower()]
    if min_price is not None:
        items = [i for i in items if i.price is not None and i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price is not None and i.price <= max_price]
    meta = {
        "source_path": MENU_SOURCE_PATH,
        "last_updated": datetime.fromtimestamp(MENU_MTIME).isoformat() if MENU_MTIME else None,
        "count": len(items),
    }
    return JSONResponse({"meta": meta, "items": [item.model_dump() for item in items]})


def log_chat(user_text: str, reply_text: str, session_id: str) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        record = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'session_id': session_id,
            'user': user_text,
            'reply': reply_text
        }
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        if not req.message or not req.message.strip():
            raise HTTPException(status_code=400, detail="Message is required")

        # Ensure menu loaded from TXT only
        refresh_menu_if_needed()

        # Ensure session id
        session_id = req.session_id or str(uuid.uuid4())

        # Update history with user message
        hist = CHAT_HISTORY.get(session_id, [])
        hist.append(("user", req.message))
        CHAT_HISTORY[session_id] = hist[-20:]

        # Generate reply (LLM or fallback)
        reply = chat_with_llm(session_id, req.message)

        # Update history with assistant reply
        CHAT_HISTORY[session_id].append(("assistant", reply))
        CHAT_HISTORY[session_id] = CHAT_HISTORY[session_id][-20:]

        # Create product suggestions
        suggestions = suggest_products(req.message, top_n=3)

        # Log conversation
        log_chat(req.message, reply, session_id)

        # Basic session cap to avoid leaks
        if len(CHAT_HISTORY) > 200:
            # drop oldest sessions
            for k in list(CHAT_HISTORY.keys())[:len(CHAT_HISTORY)-200]:
                CHAT_HISTORY.pop(k, None)

        return {"reply": reply, "session_id": session_id, "suggestions": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        # Log error and respond friendly
        try:
            log_chat(req.message if req else "", f"ERROR: {e}", req.session_id if req else "")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="حدث خطأ غير متوقع. جرّب بعد قليل لو سمحت.")


# ----- Startup -----
@app.on_event("startup")
def on_startup():
    global MENU
    MENU = load_menu(MENU_FILE)


# ----- Dev entrypoint -----
# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
