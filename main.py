"""
Square B Arabic Chatbot - FastAPI Application
مساعد دردشة ذكي لخدمة عملاء مطعم Square B
"""

import os
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from services.menu_service import MenuService
from services.chat_service import ChatService
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger()

# Initialize FastAPI app
app = FastAPI(
    title="Square B Arabic Chatbot",
    description="مساعد دردشة ذكي لخدمة عملاء مطعم Square B",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
menu_service = MenuService()
chat_service = ChatService(menu_service)

# Session storage (in-memory for demo, use Redis in production)
sessions = {}
MAX_SESSION_MESSAGES = 20


class ChatMessage(BaseModel):
    """نموذج رسالة الدردشة"""
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """نموذج طلب الدردشة"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """نموذج استجابة الدردشة"""
    response: str
    session_id: str
    timestamp: str


@app.on_event("startup")
async def startup_event():
    """تهيئة التطبيق عند البدء"""
    logger.info("🚀 Starting Square B Chatbot...")
    
    # Load menu on startup
    success = await menu_service.load_menu()
    if success:
        logger.info(f"✅ Menu loaded successfully with {len(menu_service.menu_items)} items")
    else:
        logger.error("❌ Failed to load menu")
    
    logger.info("✨ Square B Chatbot is ready!")


@app.get("/")
async def root():
    """الصفحة الرئيسية - serve HTML interface"""
    html_file = Path("static/index.html")
    if html_file.exists():
        return FileResponse("static/index.html")
    return {
        "message": "مرحباً بك في Square B Chatbot",
        "status": "active",
        "menu_items": len(menu_service.menu_items),
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """فحص صحة التطبيق"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "menu_loaded": len(menu_service.menu_items) > 0
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """
    نقطة نهاية الدردشة الرئيسية
    تتعامل مع جميع رسائل المستخدمين وتقدم ردود ذكية
    """
    try:
        # Generate or use existing session ID
        session_id = request.session_id or f"session_{datetime.now().timestamp()}"
        
        # Initialize session if doesn't exist
        if session_id not in sessions:
            sessions[session_id] = []
        
        # Add user message to session
        user_message = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        }
        sessions[session_id].append(user_message)
        
        # Keep only last MAX_SESSION_MESSAGES messages
        if len(sessions[session_id]) > MAX_SESSION_MESSAGES:
            sessions[session_id] = sessions[session_id][-MAX_SESSION_MESSAGES:]
        
        # Get chat history for context
        chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in sessions[session_id]
        ]
        
        # Generate response using chat service
        response_text = await chat_service.generate_response(
            user_message=request.message,
            chat_history=chat_history[:-1]  # Exclude current message
        )
        
        # Add assistant response to session
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        }
        sessions[session_id].append(assistant_message)
        
        # Keep only last MAX_SESSION_MESSAGES messages again
        if len(sessions[session_id]) > MAX_SESSION_MESSAGES:
            sessions[session_id] = sessions[session_id][-MAX_SESSION_MESSAGES:]
        
        logger.info(f"✅ Chat request processed for session: {session_id}")
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ في معالجة الطلب: {str(e)}"
        )


@app.get("/menu")
async def get_menu():
    """الحصول على قائمة الطعام الكاملة"""
    try:
        return {
            "success": True,
            "items": menu_service.menu_items,
            "categories": list(menu_service.categories.keys())
        }
    except Exception as e:
        logger.error(f"Error getting menu: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/menu/reload")
async def reload_menu():
    """إعادة تحميل قائمة الطعام"""
    try:
        success = await menu_service.load_menu()
        if success:
            return {
                "success": True,
                "message": "تم تحميل القائمة بنجاح",
                "items_count": len(menu_service.menu_items)
            }
        else:
            raise HTTPException(status_code=500, detail="فشل تحميل القائمة")
    except Exception as e:
        logger.error(f"Error reloading menu: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """مسح جلسة محددة"""
    if session_id in sessions:
        del sessions[session_id]
        return {"success": True, "message": "تم مسح الجلسة"}
    return {"success": False, "message": "الجلسة غير موجودة"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
