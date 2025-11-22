"""
اختبار شامل لـ Square B Chatbot
"""

import asyncio
import sys
from services.menu_service import MenuService
from services.chat_service import ChatService


async def test_menu_service():
    """اختبار خدمة القائمة"""
    print("=" * 60)
    print("🧪 اختبار خدمة القائمة (MenuService)")
    print("=" * 60)
    
    menu_service = MenuService()
    
    # Load menu
    print("\n1️⃣ تحميل القائمة...")
    success = await menu_service.load_menu()
    
    if success:
        print(f"   ✅ تم تحميل {len(menu_service.menu_items)} عنصر")
        print(f"   ✅ عدد الفئات: {len(menu_service.categories)}")
    else:
        print("   ❌ فشل تحميل القائمة")
        return None
    
    # Test search
    print("\n2️⃣ اختبار البحث...")
    test_queries = [
        "بيف",
        "chicken",
        "برقر",  # خطأ إملائي
        "بطاطا",
        "فرايز"  # خطأ إملائي
    ]
    
    for query in test_queries:
        results = menu_service.search_item(query)
        if results:
            print(f"   🔍 '{query}' -> وجدنا {len(results)} نتيجة:")
            for r in results[:2]:
                item = r['item']
                print(f"      - {menu_service.format_item_with_price(item)} (تطابق: {r['score']:.0f}%)")
        else:
            print(f"   ❌ '{query}' -> لم نجد نتائج")
    
    # Test categories
    print("\n3️⃣ الفئات الموجودة:")
    for category in menu_service.get_all_categories():
        items_count = len(menu_service.get_category_items(category))
        print(f"   📁 {category}: {items_count} عنصر")
    
    # Test delivery info
    print("\n4️⃣ معلومات التوصيل:")
    print(f"   📞 {menu_service.get_delivery_info()}")
    
    return menu_service


async def test_chat_service(menu_service: MenuService):
    """اختبار خدمة الدردشة"""
    print("\n" + "=" * 60)
    print("🧪 اختبار خدمة الدردشة (ChatService)")
    print("=" * 60)
    
    chat_service = ChatService(menu_service)
    
    # Test cases covering all 6 scenarios
    test_cases = [
        {
            "name": "1️⃣ السؤال عن السعر",
            "message": "كم سعر برجر بيف؟"
        },
        {
            "name": "2️⃣ طلب اقتراحات",
            "message": "شو بتنصحلي؟"
        },
        {
            "name": "3️⃣ طلب القائمة الكاملة",
            "message": "ورجيني المنيو كامل"
        },
        {
            "name": "4️⃣ خطأ إملائي",
            "message": "كم سعر شكن برقر"
        },
        {
            "name": "5️⃣ سؤال بالإنجليزي",
            "message": "how much is the chicken burger?"
        },
        {
            "name": "6️⃣ عنصر غير موجود",
            "message": "عندكم بيتزا؟"
        },
        {
            "name": "7️⃣ الاستفسار عن التوصيل",
            "message": "كيف أطلب توصيل؟"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print(f"   👤 المستخدم: {test_case['message']}")
        
        try:
            response = await chat_service.generate_response(
                user_message=test_case['message'],
                chat_history=[]
            )
            print(f"   🤖 البوت: {response}")
            print("   ✅ نجح الاختبار")
        except Exception as e:
            print(f"   ❌ فشل الاختبار: {str(e)}")
        
        # Small delay to avoid rate limiting
        if i < len(test_cases):
            await asyncio.sleep(1)


async def test_conversation_flow(menu_service: MenuService):
    """اختبار تدفق محادثة كاملة"""
    print("\n" + "=" * 60)
    print("🧪 اختبار تدفق المحادثة")
    print("=" * 60)
    
    chat_service = ChatService(menu_service)
    chat_history = []
    
    conversation = [
        "مرحبا",
        "شو بتنصحلي؟",
        "كم سعر Triple B؟",
        "خليها وجبة",
        "شكراً"
    ]
    
    for i, message in enumerate(conversation, 1):
        print(f"\n💬 رسالة {i}/{len(conversation)}")
        print(f"   👤 المستخدم: {message}")
        
        try:
            response = await chat_service.generate_response(
                user_message=message,
                chat_history=chat_history
            )
            print(f"   🤖 البوت: {response}")
            
            # Update chat history
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": response})
            
            # Keep last 6 messages
            if len(chat_history) > 6:
                chat_history = chat_history[-6:]
            
            print("   ✅ تم بنجاح")
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")
        
        await asyncio.sleep(1)


async def main():
    """الاختبار الرئيسي"""
    print("\n" + "🚀" * 30)
    print("   اختبار شامل لـ Square B Chatbot")
    print("🚀" * 30 + "\n")
    
    try:
        # Test menu service
        menu_service = await test_menu_service()
        
        if not menu_service:
            print("\n❌ فشل اختبار القائمة. لا يمكن المتابعة.")
            return
        
        # Test chat service (only if API key is configured)
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
        
        if api_key and api_key != "your_api_key_here":
            await test_chat_service(menu_service)
            await test_conversation_flow(menu_service)
        else:
            print("\n⚠️ API Key غير مكوّن. تم تخطي اختبارات الدردشة.")
            print("   قم بتعيين OPENAI_API_KEY أو API_KEY في ملف .env")
        
        print("\n" + "=" * 60)
        print("✅ اكتملت جميع الاختبارات")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ خطأ عام في الاختبار: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
