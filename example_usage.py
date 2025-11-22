"""
أمثلة على استخدام Square B Chatbot API
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

def test_chat(message: str, session_id: str = None):
    """اختبار endpoint الدردشة"""
    print(f"\n{'='*60}")
    print(f"👤 المستخدم: {message}")
    print(f"{'='*60}")
    
    payload = {
        "message": message
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"🤖 البوت: {data['response']}")
            print(f"\n📊 معلومات الجلسة:")
            print(f"   - Session ID: {data['session_id']}")
            print(f"   - Timestamp: {data['timestamp']}")
            return data['session_id']
        else:
            print(f"❌ خطأ: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")
        return None


def test_health():
    """فحص صحة التطبيق"""
    print(f"\n{'='*60}")
    print("🏥 فحص صحة التطبيق")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ الحالة: {data['status']}")
            print(f"✅ القائمة محملة: {data['menu_loaded']}")
            print(f"✅ الوقت: {data['timestamp']}")
        else:
            print(f"❌ خطأ: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


def test_menu():
    """عرض القائمة"""
    print(f"\n{'='*60}")
    print("📋 عرض القائمة")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/menu")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ عدد العناصر: {len(data['items'])}")
            print(f"✅ الفئات: {', '.join(data['categories'])}")
            
            # Show first few items
            print("\n🍔 بعض العناصر:")
            for item in data['items'][:5]:
                name = item.get('name', '')
                price = item.get('price_regular_formatted', '')
                print(f"   - {name}: {price}")
        else:
            print(f"❌ خطأ: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")


def run_conversation_test():
    """اختبار محادثة كاملة"""
    print("\n" + "🚀" * 30)
    print("   اختبار محادثة كاملة")
    print("🚀" * 30)
    
    # Check health first
    test_health()
    
    # Test menu
    test_menu()
    
    # Conversation flow
    messages = [
        "مرحبا",
        "شو بتنصحلي؟",
        "كم سعر Triple B؟",
        "عندكم بطاطا؟",
        "ورجيني المنيو",
        "رقم التوصيل",
        "شكراً"
    ]
    
    session_id = None
    for message in messages:
        session_id = test_chat(message, session_id)
        if not session_id:
            print("❌ فشلت المحادثة")
            break
    
    print("\n" + "=" * 60)
    print("✅ اكتمل اختبار المحادثة")
    print("=" * 60)


def run_specific_tests():
    """اختبارات محددة للحالات الستة"""
    print("\n" + "🧪" * 30)
    print("   اختبار الحالات الستة")
    print("🧪" * 30)
    
    test_cases = [
        "كم سعر برجر بيف؟",           # 1. Price query
        "شو بتنصحلي؟",                # 2. Suggestion
        "ورجيني المنيو كامل",         # 3. Full menu
        "كم سعر شكن برقر",            # 4. Spelling error
        "how much is the chicken burger?",  # 5. English query
        "عندكم بيتزا؟"                # 6. Item not found
    ]
    
    for message in test_cases:
        test_chat(message)
    
    print("\n" + "=" * 60)
    print("✅ اكتملت جميع الاختبارات")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    print("\n" + "🍔" * 30)
    print("   Square B Chatbot - API Testing")
    print("🍔" * 30)
    print("\nتأكد من تشغيل الخادم أولاً: python main.py")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "conversation":
            run_conversation_test()
        elif sys.argv[1] == "specific":
            run_specific_tests()
        elif sys.argv[1] == "health":
            test_health()
        elif sys.argv[1] == "menu":
            test_menu()
        else:
            print(f"❌ خيار غير معروف: {sys.argv[1]}")
            print("الخيارات المتاحة: conversation, specific, health, menu")
    else:
        # Run all tests
        run_specific_tests()
