from sqlalchemy.orm import Session
from database import User, Document, Conversation, ConversationThread, ConversationMessage, SessionLocal
from datetime import datetime
import hashlib
import json
import uuid

def get_or_create_user(session_id: str, db: Session) -> User:
    """Get existing user or create new one based on session_id"""
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user:
        user = User(session_id=session_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_user(session_id: str, db: Session) -> User:
    """Get existing user without creating one"""
    return db.query(User).filter(User.session_id == session_id).first()

def save_document(
    document_id: str,
    filename: str,
    document_type: str,
    content: str,
    analysis_result: dict,
    session_id: str,
    db: Session
) -> Document:
    """Save document to database"""
    # Create content hash for deduplication
    content_hash = hashlib.md5(content.encode()).hexdigest()
    
    # Check if document already exists for this user
    existing_doc = db.query(Document).filter(
        Document.content_hash == content_hash,
        Document.user_id == get_or_create_user(session_id, db).id
    ).first()
    
    if existing_doc:
        return existing_doc
    
    # Create new document
    user = get_or_create_user(session_id, db)
    document = Document(
        document_id=document_id,
        filename=filename,
        document_type=document_type,
        content_hash=content_hash,
        content=content,
        summary=json.dumps(analysis_result),
        risk_score=analysis_result.get('risk_score', 0.0),
        user_id=user.id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

def save_conversation(
    question: str,
    answer: str,
    document_id: str,
    session_id: str,
    db: Session
) -> Conversation:
    """Save conversation to database"""
    user = get_or_create_user(session_id, db)
    
    # Find the document
    document = db.query(Document).filter(
        Document.document_id == document_id,
        Document.user_id == user.id
    ).first()
    
    if not document:
        raise ValueError(f"Document {document_id} not found for user {session_id}")
    
    conversation = Conversation(
        question=question,
        answer=answer,
        user_id=user.id,
        document_id=document.id
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def get_user_conversations(session_id: str, db: Session, limit: int = 50) -> list:
    """Get recent conversations for a user"""
    user = get_user(session_id, db)
    if not user:
        return []  # No user, no conversations
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).order_by(Conversation.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": conv.id,
            "question": conv.question,
            "answer": conv.answer,
            "timestamp": conv.timestamp.isoformat(),
            "document_name": conv.document.filename if conv.document else "Unknown"
        }
        for conv in conversations
    ]

def get_user_documents(session_id: str, db: Session) -> list:
    """Get all documents for a user"""
    user = get_user(session_id, db)
    if not user:
        return []  # No user, no documents
    documents = db.query(Document).filter(
        Document.user_id == user.id
    ).order_by(Document.upload_date.desc()).all()
    
    return [
        {
            "id": doc.id,
            "document_id": doc.document_id,
            "filename": doc.filename,
            "document_type": doc.document_type,
            "risk_score": doc.risk_score,
            "upload_date": doc.upload_date.isoformat(),
            "summary": json.loads(doc.summary) if doc.summary else {}
        }
        for doc in documents
    ]

def get_document_by_id(document_id: str, session_id: str, db: Session) -> Document:
    """Get document by document_id for a specific user"""
    user = get_user(session_id, db)
    if not user:
        return None
    return db.query(Document).filter(
        Document.document_id == document_id,
        Document.user_id == user.id
    ).first()

def delete_document(document_id: str, session_id: str, db: Session) -> bool:
    """Delete document and all its conversations"""
    user = get_user(session_id, db)
    if not user:
        return False
    document = db.query(Document).filter(
        Document.document_id == document_id,
        Document.user_id == user.id
    ).first()
    
    if document:
        # Delete related conversations first
        db.query(Conversation).filter(Conversation.document_id == document.id).delete()
        # Delete document
        db.delete(document)
        db.commit()
        return True
    return False

def create_conversation_thread(session_id: str, title: str = None, db: Session = None) -> ConversationThread:
    """Create a new conversation thread"""
    if db is None:
        db = SessionLocal()
        try:
            return create_conversation_thread(session_id, title, db)
        finally:
            db.close()
    
    user = get_or_create_user(session_id, db)
    thread_id = str(uuid.uuid4())
    
    thread = ConversationThread(
        thread_id=thread_id,
        title=title or "New Chat",
        user_id=user.id
    )
    
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread

def add_message_to_thread(
    thread_id: str, 
    role: str, 
    content: str, 
    session_id: str, 
    document_id: str = None,
    db: Session = None
) -> ConversationMessage:
    """Add a message to a conversation thread"""
    if db is None:
        db = SessionLocal()
        try:
            return add_message_to_thread(thread_id, role, content, session_id, document_id, db)
        finally:
            db.close()
    
    user = get_user(session_id, db)
    if not user:
        raise ValueError(f"User not found for session {session_id}")
    
    # Find the thread
    thread = db.query(ConversationThread).filter(
        ConversationThread.thread_id == thread_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if not thread:
        raise ValueError(f"Thread {thread_id} not found for user {session_id}")
    
    # Find document if document_id provided
    document_db_id = None
    if document_id:
        document = db.query(Document).filter(
            Document.document_id == document_id,
            Document.user_id == user.id
        ).first()
        if document:
            document_db_id = document.id
    
    message = ConversationMessage(
        thread_id=thread.id,
        role=role,
        content=content,
        document_id=document_db_id
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Update thread's updated_at timestamp
    thread.updated_at = datetime.utcnow()
    db.commit()
    
    return message

def get_user_threads(session_id: str, db: Session = None) -> list:
    """Get all conversation threads for a user"""
    if db is None:
        db = SessionLocal()
        try:
            return get_user_threads(session_id, db)
        finally:
            db.close()
    
    user = get_user(session_id, db)
    if not user:
        return []
    
    threads = db.query(ConversationThread).filter(
        ConversationThread.user_id == user.id
    ).order_by(ConversationThread.updated_at.desc()).all()
    
    return [
        {
            "id": thread.id,
            "thread_id": thread.thread_id,
            "title": thread.title,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
            "message_count": len(thread.messages)
        }
        for thread in threads
    ]

def get_thread_messages(thread_id: str, session_id: str, db: Session = None) -> list:
    """Get all messages in a conversation thread"""
    if db is None:
        db = SessionLocal()
        try:
            return get_thread_messages(thread_id, session_id, db)
        finally:
            db.close()
    
    user = get_user(session_id, db)
    if not user:
        return []
    
    thread = db.query(ConversationThread).filter(
        ConversationThread.thread_id == thread_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if not thread:
        return []
    
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.thread_id == thread.id
    ).order_by(ConversationMessage.timestamp.asc()).all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "document_id": msg.document.document_id if msg.document else None
        }
        for msg in messages
    ]

def delete_thread(thread_id: str, session_id: str, db: Session = None) -> bool:
    """Delete a conversation thread and all its messages"""
    if db is None:
        db = SessionLocal()
        try:
            return delete_thread(thread_id, session_id, db)
        finally:
            db.close()
    
    user = get_user(session_id, db)
    if not user:
        return False
    
    thread = db.query(ConversationThread).filter(
        ConversationThread.thread_id == thread_id,
        ConversationThread.user_id == user.id
    ).first()
    
    if thread:
        # Messages will be deleted automatically due to cascade
        db.delete(thread)
        db.commit()
        return True
    return False
