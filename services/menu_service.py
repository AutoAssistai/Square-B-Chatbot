"""
Menu Service - قراءة وإدارة قائمة الطعام من MENU.txt
"""

import os
import re
from typing import Dict, List, Optional
from pathlib import Path
from rapidfuzz import fuzz, process
from utils.logger import setup_logger

logger = setup_logger()


class MenuService:
    """خدمة إدارة قائمة الطعام"""
    
    def __init__(self):
        self.menu_file = os.getenv("MENU_TXT", "MENU.txt")
        self.menu_items: List[Dict] = []
        self.categories: Dict[str, List[Dict]] = {}
        self.all_item_names: List[str] = []
        self.raw_menu_text: str = ""
        
    async def load_menu(self) -> bool:
        """
        تحميل قائمة الطعام من MENU.txt
        """
        try:
            menu_path = Path(self.menu_file)
            
            if not menu_path.exists():
                logger.error(f"Menu file not found: {self.menu_file}")
                return False
            
            with open(menu_path, 'r', encoding='utf-8') as f:
                self.raw_menu_text = f.read()
            
            # Parse menu
            self._parse_menu()
            
            logger.info(f"✅ Menu loaded: {len(self.menu_items)} items in {len(self.categories)} categories")
            return True
            
        except Exception as e:
            logger.error(f"Error loading menu: {str(e)}", exc_info=True)
            return False
    
    def _parse_menu(self):
        """
        تحليل محتوى MENU.txt واستخراج العناصر والأسعار
        """
        lines = self.raw_menu_text.split('\n')
        current_category = None
        current_subcategory = None
        pending_arabic_translation = None
        
        self.menu_items = []
        self.categories = {}
        
        # Extract delivery number
        delivery_match = re.search(r'DELIVERY[:\s]+(\d+)', self.raw_menu_text, re.IGNORECASE)
        if delivery_match:
            self.delivery_number = delivery_match.group(1)
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines and separators
            if not line or line.startswith('---'):
                continue
            
            # Check for category headers
            if line.startswith('##') and not line.startswith('###'):
                category_match = re.search(r'##\s*[🍔🍟🥤👶🧂]*\s*(.+)', line)
                if category_match:
                    current_category = category_match.group(1).strip()
                    if current_category not in self.categories:
                        self.categories[current_category] = []
                continue
            
            elif line.startswith('###'):
                subcategory_match = re.search(r'###\s*(.+)', line)
                if subcategory_match:
                    current_subcategory = subcategory_match.group(1).strip()
                continue
            
            # Parse table rows for burger items
            if '|' in line and 'دينار' in line:
                self._parse_table_row(line, current_category, current_subcategory)
            
            # Check if line is Arabic translation (no English, has Arabic letters)
            elif re.search(r'[\u0600-\u06FF]', line) and not line.startswith('-') and not line.startswith('**'):
                pending_arabic_translation = line
            
            # Parse list items (KIDS MENU, SIDES, DRINKS, SAUCES)
            elif line.startswith('-') or line.startswith('•'):
                self._parse_list_item(line, current_category, pending_arabic_translation)
                pending_arabic_translation = None
        
        # Build item names list for fuzzy matching (with all aliases)
        self.all_item_names = []
        for item in self.menu_items:
            # Add main name
            if item.get('name'):
                self.all_item_names.append(item['name'])
            # Add Arabic name if different
            if item.get('name_ar') and item['name_ar'] != item.get('name'):
                self.all_item_names.append(item['name_ar'])
            # Add search aliases
            if item.get('search_aliases'):
                self.all_item_names.extend(item['search_aliases'])
    
    def _parse_table_row(self, line: str, category: str, subcategory: str):
        """تحليل صف من جدول البرجر"""
        parts = [p.strip() for p in line.split('|') if p.strip()]
        
        if len(parts) < 3:
            return
        
        # Extract size and prices
        size = parts[0]
        
        # Skip header rows
        if 'Size' in size or 'Regular' in size or '---' in size:
            return
        
        # Extract regular price
        regular_match = re.search(r'(\d+\.\d+)\s*دينار', parts[1])
        if not regular_match:
            return
        
        regular_price = regular_match.group(1)
        
        # Extract meal price if exists
        meal_price = None
        if len(parts) > 2:
            meal_match = re.search(r'(\d+\.\d+)\s*دينار', parts[2])
            if meal_match:
                meal_price = meal_match.group(1)
        
        # Create item
        item_name = f"{subcategory} {size}" if subcategory else size
        
        # Build search aliases
        search_aliases = []
        if subcategory:
            search_aliases.append(subcategory)
            subcategory_lower = subcategory.lower()
            if 'beef' in subcategory_lower:
                search_aliases.extend(['بيف', 'لحم', 'لحمة', 'beef', 'لحم بقري'])
            if 'chicken' in subcategory_lower:
                search_aliases.extend(['دجاج', 'شكن', 'chicken', 'فراخ'])
            if 'triple' in subcategory_lower:
                search_aliases.extend(['تريبل', 'triple'])
            if 'fire' in subcategory_lower:
                search_aliases.extend(['حار', 'فاير', 'fire', 'حراق'])
        search_aliases.extend(['برجر', 'برقر', 'burger', 'ساندوتش'])
        
        item = {
            'name': item_name,
            'name_ar': item_name,
            'category': category,
            'subcategory': subcategory,
            'size': size,
            'price_regular': regular_price,
            'price_regular_formatted': f"{regular_price} دينار",
            'type': 'regular',
            'search_aliases': search_aliases
        }
        
        self.menu_items.append(item)
        
        if category:
            self.categories.setdefault(category, []).append(item)
        
        # Add meal version if exists
        if meal_price:
            meal_item = item.copy()
            meal_item['name'] = f"{item_name} وجبة"
            meal_item['price_regular'] = meal_price
            meal_item['price_regular_formatted'] = f"{meal_price} دينار"
            meal_item['type'] = 'meal'
            meal_item['search_aliases'] = search_aliases + ['وجبة', 'meal', 'ميل']
            
            self.menu_items.append(meal_item)
            if category:
                self.categories[category].append(meal_item)
    
    def _parse_list_item(self, line: str, category: str, arabic_translation: str = None):
        """تحليل عنصر من القائمة (KIDS, SIDES, DRINKS, SAUCES)"""
        # Remove bullet points
        line = re.sub(r'^[-•]\s*', '', line).strip()
        
        # Extract name and price
        price_match = re.search(r'(.+?)\s*-\s*(\d+\.\d+)\s*دينار', line)
        
        if price_match:
            name = price_match.group(1).strip()
            price = price_match.group(2)
            
            # Remove markdown formatting (**, etc.)
            name_clean = re.sub(r'\*\*', '', name).strip()
            
            # Build search aliases
            search_aliases = []
            
            # Add common variations
            name_lower = name_clean.lower()
            if 'beef' in name_lower:
                search_aliases.extend(['بيف', 'لحم', 'لحمة', 'beef', 'لحم بقري'])
            if 'chicken' in name_lower:
                search_aliases.extend(['دجاج', 'شكن', 'chicken', 'فراخ'])
            if 'burger' in name_lower:
                search_aliases.extend(['برجر', 'برقر', 'burger', 'ساندوتش'])
            if 'fries' in name_lower or 'بطاطا' in name_lower:
                search_aliases.extend(['بطاطا', 'بطاطس', 'فرايز', 'fries', 'بطاط'])
            if 'cheese' in name_lower:
                search_aliases.extend(['جبنة', 'جبن', 'cheese'])
            if 'mozzarella' in name_lower:
                search_aliases.extend(['موزاريلا', 'موزريلا', 'mozzarella'])
            if 'jalapeno' in name_lower or 'jalapeño' in name_lower:
                search_aliases.extend(['هالابينو', 'جلابينو', 'jalapeno', 'هلابينو'])
            if 'pop corn' in name_lower or 'popcorn' in name_lower:
                search_aliases.extend(['بوب كورن', 'فشار دجاج', 'popcorn'])
            
            # Use Arabic translation if provided
            name_ar = arabic_translation if arabic_translation else name_clean
            
            item = {
                'name': name_clean,
                'name_ar': name_ar,
                'category': category,
                'price_regular': price,
                'price_regular_formatted': f"{price} دينار",
                'type': 'item',
                'search_aliases': search_aliases
            }
            
            self.menu_items.append(item)
            
            if category:
                self.categories.setdefault(category, []).append(item)
    
    def search_item(self, query: str, threshold: int = 60) -> List[Dict]:
        """
        البحث عن عنصر في القائمة باستخدام fuzzy matching
        
        Args:
            query: نص البحث
            threshold: الحد الأدنى للتطابق (0-100)
        
        Returns:
            قائمة بالعناصر المطابقة
        """
        if not query or not self.all_item_names:
            return []
        
        # Use rapidfuzz for fuzzy matching
        matches = process.extract(
            query,
            self.all_item_names,
            scorer=fuzz.WRatio,
            limit=10
        )
        
        # Filter by threshold and get full item details
        results = []
        seen_items = set()  # Track items we've already added
        
        for match_text, score, _ in matches:
            if score >= threshold:
                # Find the full item that matches
                for item in self.menu_items:
                    # Create unique item ID to avoid duplicates
                    item_id = f"{item['name']}_{item.get('price_regular')}"
                    
                    if item_id in seen_items:
                        continue
                    
                    # Check if match_text matches this item
                    if (item['name'] == match_text or 
                        item.get('name_ar') == match_text or
                        (item.get('search_aliases') and match_text in item.get('search_aliases', []))):
                        
                        results.append({
                            'item': item,
                            'score': score
                        })
                        seen_items.add(item_id)
                        break
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:5]  # Return top 5
    
    def get_category_items(self, category: str) -> List[Dict]:
        """الحصول على جميع عناصر فئة معينة"""
        return self.categories.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """الحصول على جميع الفئات"""
        return list(self.categories.keys())
    
    def format_item_with_price(self, item: Dict) -> str:
        """
        تنسيق عنصر مع السعر بالصيغة المطلوبة
        """
        name = item.get('name_ar', item.get('name', ''))
        price = item.get('price_regular_formatted', f"{item.get('price_regular', '0.00')} دينار")
        
        return f"{name} - {price}"
    
    def get_delivery_info(self) -> str:
        """الحصول على معلومات التوصيل"""
        if hasattr(self, 'delivery_number'):
            return f"رقم التوصيل: {self.delivery_number}"
        return "رقم التوصيل: 0797920111"
