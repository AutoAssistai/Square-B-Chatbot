"""
Chat Service - خدمة الدردشة الذكية مع LLM
"""

import os
import re
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from utils.logger import setup_logger
from services.menu_service import MenuService

logger = setup_logger()


class ChatService:
    """خدمة الدردشة الذكية"""
    
    def __init__(self, menu_service: MenuService):
        self.menu_service = menu_service
        
        # Load API configuration from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("MODEL", "gpt-3.5-turbo")
        self.api_base_url = os.getenv("API_BASE_URL")
        
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable is not set!")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize OpenAI client
        client_kwargs = {"api_key": self.api_key}
        if self.api_base_url:
            client_kwargs["base_url"] = self.api_base_url
            logger.info(f"Using custom API base URL: {self.api_base_url}")
        
        self.client = AsyncOpenAI(**client_kwargs)
        
        # LLM parameters for optimal performance
        self.max_tokens = 500  # Keep responses concise
        self.temperature = 0.7  # Balance between creativity and consistency
        
        logger.info(f"ChatService initialized with model: {self.model}")
    
    async def generate_response(
        self,
        user_message: str,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        توليد رد ذكي على رسالة المستخدم
        
        Args:
            user_message: رسالة المستخدم
            chat_history: سجل المحادثة السابقة
        
        Returns:
            رد المساعد بالعربي
        """
        try:
            # Analyze user intent
            intent = self._analyze_intent(user_message)
            logger.info(f"User intent detected: {intent}")
            
            # Search for relevant menu items
            relevant_items = self._get_relevant_items(user_message, intent)
            
            # Build context for LLM
            context = self._build_context(intent, relevant_items)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(context)
            
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add chat history (last few messages for context)
            if chat_history:
                messages.extend(chat_history[-6:])  # Last 3 exchanges
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            assistant_response = response.choices[0].message.content.strip()
            
            logger.info(f"Response generated successfully")
            return assistant_response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            return "عذراً، حدث خطأ في معالجة طلبك. الرجاء المحاولة مرة أخرى."
    
    def _analyze_intent(self, message: str) -> str:
        """
        تحليل نية المستخدم من الرسالة
        
        Returns:
            نوع النية: price_query, full_menu, suggestion, item_not_found, general
        """
        message_lower = message.lower()
        
        # Price query keywords
        price_keywords = ['سعر', 'كم', 'بكم', 'price', 'cost', 'how much', 'قديش']
        if any(keyword in message_lower for keyword in price_keywords):
            return 'price_query'
        
        # Full menu request
        menu_keywords = ['منيو', 'قائمة', 'menu', 'كل', 'all', 'شو عندكم', 'ايش عندكم']
        if any(keyword in message_lower for keyword in menu_keywords):
            return 'full_menu'
        
        # Suggestion request
        suggestion_keywords = ['نصح', 'اقترح', 'suggest', 'recommend', 'شو بتنصح', 'ايش بتنصح', 'افضل']
        if any(keyword in message_lower for keyword in suggestion_keywords):
            return 'suggestion'
        
        # Greeting
        greeting_keywords = ['مرحب', 'هلا', 'السلام', 'صباح', 'مساء', 'hello', 'hi']
        if any(keyword in message_lower for keyword in greeting_keywords):
            return 'greeting'
        
        # Delivery inquiry
        delivery_keywords = ['توصيل', 'delivery', 'رقم', 'تواصل', 'اتصال']
        if any(keyword in message_lower for keyword in delivery_keywords):
            return 'delivery'
        
        return 'general'
    
    def _get_relevant_items(self, message: str, intent: str) -> List[Dict]:
        """
        الحصول على العناصر ذات الصلة من القائمة
        """
        # For full menu request, return all items
        if intent == 'full_menu':
            return self.menu_service.menu_items
        
        # For delivery or greeting, return empty
        if intent in ['delivery', 'greeting']:
            return []
        
        # Search for items in the message
        results = self.menu_service.search_item(message, threshold=60)
        
        # If items found, return them
        if results:
            return [r['item'] for r in results[:5]]
        
        # For suggestions, return some popular items
        if intent == 'suggestion':
            popular_items = []
            # Get some burgers
            burgers = self.menu_service.get_category_items('BURGERS')
            if burgers:
                popular_items.extend(burgers[:4])
            # Get some sides
            sides = self.menu_service.get_category_items('SIDES')
            if sides:
                popular_items.extend(sides[:3])
            return popular_items
        
        return []
    
    def _build_context(self, intent: str, items: List[Dict]) -> str:
        """
        بناء السياق من عناصر القائمة
        """
        if not items:
            return ""
        
        context_parts = []
        
        if intent == 'full_menu':
            # Group by category for full menu
            for category in self.menu_service.get_all_categories():
                cat_items = self.menu_service.get_category_items(category)
                if cat_items:
                    context_parts.append(f"\n{category}:")
                    for item in cat_items[:10]:  # Limit items per category
                        formatted = self.menu_service.format_item_with_price(item)
                        context_parts.append(f"  - {formatted}")
        else:
            # List specific items
            context_parts.append("\nعناصر القائمة ذات الصلة:")
            for item in items:
                formatted = self.menu_service.format_item_with_price(item)
                context_parts.append(f"  - {formatted}")
        
        return "\n".join(context_parts)
    
    def _build_system_prompt(self, context: str) -> str:
        """
        بناء System Prompt للـ LLM
        """
        delivery_info = self.menu_service.get_delivery_info()
        
        prompt = f"""أنت مساعد دردشة ذكي وراقي لخدمة عملاء مطعم Square B - مطعم برجر فاخر.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ قواعد مطلقة - لا استثناءات:

1. **الدقة المطلقة**: 
   - اعتمد حصرياً على المعلومات من السياق أدناه
   - لا تخترع أي صنف، سعر، أو معلومة غير موجودة
   - إذا لم تجد المعلومة، اعتذر واقترح بديل من القائمة

2. **صيغة الأسعار الإلزامية**:
   - دائماً: "X.XX دينار" (مثال: 3.50 دينار)
   - ممنوع: JD, JOD, دينار أردني، أو أي صيغة أخرى
   - لا تحويلات عملات، لا تقديرات

3. **اللغة والأسلوب**:
   - كل الردود بالعربي الأردني الطبيعي والراقي
   - حتى لو كتب المستخدم بالإنجليزي → رد بالعربي
   - أسلوب ودود، مهذب، احترافي، مختصر

4. **النصوص فقط**:
   - لا صور للمنتجات
   - لا بطاقات HTML
   - لا روابط
   - فقط نص عربي واضح ومنسق

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 أنواع الطلبات وكيفية التعامل:

أ) سؤال عن السعر:
   → أعط السعر الدقيق من السياق
   → اقترح صنف مكمّل (Upsell/Cross-sell) من نفس الفئة
   → مثال: "برجر البيف 1x1 بـ 3.50 دينار. تحب تخليه وجبة بـ 4.75 دينار؟"

ب) طلب القائمة الكاملة:
   → اعرض قائمة منظمة بالفئات
   → اذكر 3-4 أصناف من كل فئة مع الأسعار
   → لا تكرر كل شيء، كن انتقائياً

ج) طلب اقتراحات:
   → اقترح 2-3 أصناف مميزة مع الأسعار
   → من فئات مختلفة (برجر + جانبي + مشروب)
   → أضف سؤال متابعة: "شو رأيك؟"

د) أخطاء إملائية:
   → افهم القصد (fuzzy matching مفعّل)
   → رد بالمعلومة الصحيحة
   → لا تذكر الخطأ

هـ) سؤال بالإنجليزي:
   → افهم السؤال
   → رد بالعربي الأردني
   → أعط المعلومة المطلوبة

و) عنصر غير موجود:
   → اعتذر بلطف: "للأسف ما عنا هالصنف 😊"
   → اقترح بديل قريب من القائمة
   → مثال: "بس عنا برجرات لذيذة! جرّب Triple B؟"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 الاقتراحات الذكية (Upsell/Cross-sell):

- اقترح وجبة كاملة بدل ساندوتش منفرد
- اقترح حجم أكبر إذا مناسب
- اقترح أصناف من نفس الفئة أو السعر
- لا تبالغ، اقتراح واحد أو اثنين كافي
- اجعلها طبيعية: "تحب تضيف بطاطا؟"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 معلومات الاتصال:
{delivery_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 السياق من قائمة Square B:

{context if context else "لا توجد عناصر محددة في هذا السياق."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ تذكر دائماً:
• كن ودياً وطبيعياً
• مختصر ومباشر
• دقيق 100% (من السياق فقط)
• اقتراحات ذكية ومناسبة
• أسلوب راقٍ يناسب المطعم"""

        return prompt
