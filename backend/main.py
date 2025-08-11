from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile
import shutil
from pathlib import Path
import io
import csv
from typing import Dict, Any, List
import json
from datetime import datetime
import pdfplumber
import PyPDF2
from docx import Document
import openpyxl
import google.generativeai as genai
from dotenv import load_dotenv
import uuid
import re
from sqlalchemy.orm import Session

# Database imports
from database import create_tables, get_db
from db_service import (
    save_document, save_conversation, get_user_conversations,
    get_user_documents, get_document_by_id, delete_document,
    create_conversation_thread, add_message_to_thread, get_user_threads,
    get_thread_messages, delete_thread, save_document_to_thread, get_thread_documents
)

# Load environment variables explicitly from backend/.env regardless of CWD
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Initialize FastAPI app
app = FastAPI(
    title="FinanceBot with Gemini",
    description="AI-powered financial document analysis using Google Gemini",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


gemini_api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
try:
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        # No API key present; avoid initializing the model so we can surface a clear message
        model = None
except Exception:
    model = None

# Initialize database
create_tables()

# Simple in-memory storage (keeping for backward compatibility)
documents = {}

def get_session_id(request: Request) -> str:
    """Get or create session ID from request"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF"""
    text = ""
    
    # Try pdfplumber first
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber extraction failed: {e}")
    
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"PyPDF2 extraction failed: {e}")
    
    if not text.strip():
        return "Could not extract text from PDF - file may be corrupted, password-protected, or contain only images"
    return text

def extract_docx_text(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        doc = Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
        if not text.strip():
            return "Document appears to be empty or contains no extractable text"
        return text
    except Exception as e:
        print(f"DOCX extraction failed: {e}")
        return f"Failed to extract text from DOCX: {str(e)}"

def extract_csv_text(file_path: str) -> str:
    try:
        lines = []
        with open(file_path, newline='', encoding='utf-8', errors='ignore') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                lines.append(", ".join(cell.strip() for cell in row))
        text = "\n".join(lines)
        if not text.strip():
            return "CSV file appears to be empty or contains no data"
        return text
    except Exception as e:
        print(f"CSV extraction failed: {e}")
        return f"Failed to extract text from CSV: {str(e)}"

def extract_xlsx_text(file_path: str) -> str:
    wb = None
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(cell) if cell is not None else '' for cell in row]
                lines.append(", ".join(cells))
        text = "\n".join(lines)
        if not text.strip():
            return "Excel file appears to be empty or contains no data"
        return text
    except Exception as e:
        print(f"XLSX extraction failed: {e}")
        return f"Failed to extract text from Excel: {str(e)}"
    finally:
        try:
            if wb is not None:
                wb.close()
        except Exception as e:
            print(f"Failed to close Excel workbook: {e}")

def analyze_with_ai(text: str, filename: str) -> Dict[str, Any]:
    """Get AI analysis using Google Gemini"""
    try:
        if not model:
            # Provide a friendly fallback response when LLM is not available
            return {
                "ai_analysis": "Hi there! 👋 I'd love to analyze your financial document, but I need my AI brain (Gemini API) to be configured first. Please add your GEMINI_API_KEY to the .env file and I'll be happy to help analyze your documents!",
                "risk_score": 0.0,
                "document_type": "unknown"
            }
        
        prompt = f"""
        Hey! I'm your friendly financial assistant. I'm looking at this document: {filename}

        Here's what I found in it: {text[:3000]}

        Can you help me analyze this by providing:
        1. What type of document this is (bank statement, invoice, annual report, transaction history, or something else)
        2. 3-5 key financial insights in a friendly, conversational tone
        3. A risk score from 0-10 (where 0 = no worries, 10 = needs immediate attention)
        4. Any unusual patterns or things that seem suspicious
        5. Some helpful recommendations in a friendly way

        Keep it conversational and helpful, like you're talking to a friend about their finances!
        """
        
        response = model.generate_content(prompt)
        ai_response = response.text
        
        if not ai_response or not ai_response.strip():
            return {
                "ai_analysis": "Oops! My AI brain seems to be having a moment. Let me try to analyze this document manually for you.",
                "risk_score": 0.0,
                "document_type": "unknown"
            }
        
        # Extract risk score from response
        risk_score = 3.0  # default
        risk_match = re.search(r'risk.*?(\d+(?:\.\d+)?)', ai_response.lower())
        if risk_match:
            try:
                risk_score = min(10.0, max(0.0, float(risk_match.group(1))))
            except:
                pass
        
        # Extract document type
        doc_type = "financial_document"
        if "bank" in ai_response.lower() or "statement" in ai_response.lower():
            doc_type = "bank_statement"
        elif "invoice" in ai_response.lower() or "bill" in ai_response.lower():
            doc_type = "invoice"
        elif "annual" in ai_response.lower() or "report" in ai_response.lower():
            doc_type = "annual_report"
        elif "transaction" in ai_response.lower():
            doc_type = "transaction_history"
        
        return {
            "ai_analysis": ai_response,
            "risk_score": risk_score,
            "document_type": doc_type
        }
        
    except Exception as e:
        error_msg = f"Hey there! 😅 I ran into a little issue while analyzing your document: {str(e)}"
        if "API key" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "Hi! 👋 I'm having trouble with my AI brain (Gemini API). It looks like the API key might be invalid or expired. Could you check your GEMINI_API_KEY in the .env file?"
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "Hey! 😊 I've hit my AI brain's limit for today. Don't worry though - you can still upload and view your documents! Try again later when my brain has had a rest."
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_msg = "Hi there! 🌐 I'm having trouble connecting to my AI brain right now. Could you check your internet connection? I'm here to help once we get connected!"
        
        print(f"AI analysis failed for {filename}: {error_msg}")
        return {
            "ai_analysis": error_msg,
            "risk_score": 0.0,
            "document_type": "unknown"
        }

def extract_text_by_extension(file_path: str, filename_lower: str) -> str:
    if filename_lower.endswith('.pdf'):
        return extract_pdf_text(file_path)
    if filename_lower.endswith('.docx'):
        return extract_docx_text(file_path)
    if filename_lower.endswith('.csv'):
        return extract_csv_text(file_path)
    if filename_lower.endswith('.xlsx'):
        return extract_xlsx_text(file_path)
    return ""

@app.get("/")
async def root():
    return {
        "message": "FinanceBot API with Google Gemini",
        "status": "running",
        "gemini_configured": bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')),
        "model": "gemini-pro"
    }

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    thread_id: str = Form(None)
):
    """Upload and analyze document (pdf, docx, csv, xlsx)"""

    filename_lower = file.filename.lower()
    allowed_suffixes = ('.pdf', '.docx', '.csv', '.xlsx')
    if not filename_lower.endswith(allowed_suffixes):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Allowed: .pdf, .docx, .csv, .xlsx",
        )

    suffix = Path(file.filename).suffix or '.dat'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        text = extract_text_by_extension(tmp_path, filename_lower)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text found in PDF")
        
        # Analyze with AI
        analysis = analyze_with_ai(text, file.filename)
        
        # Create response
        doc_id = str(uuid.uuid4())
        result = {
            "document_id": doc_id,
            "filename": file.filename,
            "document_type": analysis["document_type"],
            "processed_at": datetime.now().isoformat(),
            "summary": {
                "total_transactions": 0,
                "total_amount": 0.0,
                "date_range": {},
                "key_insights": [analysis["ai_analysis"][:300]]
            },
            "transactions": [],
            "anomalies": [],
            "risk_score": analysis["risk_score"],
            "recommendations": ["Review the AI analysis for insights"],
            "extractable_data": {"text_preview": text[:300]}
        }
        
        # Store document (in-memory for compatibility)
        documents[doc_id] = {
            "result": result,
            "full_text": text,
            "ai_analysis": analysis["ai_analysis"]
        }

        # Persist to DB and optionally associate with a thread
        try:
            session_id = get_session_id(request)
            save_document(
                document_id=doc_id,
                filename=file.filename,
                document_type=analysis["document_type"],
                content=text,
                analysis_result=result,
                session_id=session_id,
                db=db
            )
            if thread_id:
                save_document_to_thread(thread_id=thread_id, document_id=doc_id, session_id=session_id, db=db)
        except Exception as e:
            print(f"Database save error for {file.filename}: {e}")

        return result
    
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            try:
                import time
                time.sleep(0.1)
                os.unlink(tmp_path)
            except Exception:
                pass

@app.post("/upload-multiple")
async def upload_multiple(
    files: List[UploadFile] = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    thread_id: str = Form(None)
):
    """Upload and analyze multiple documents (pdf, docx, csv, xlsx)"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    session_id = get_session_id(request)
    results: List[Dict[str, Any]] = []
    previews: List[Dict[str, str]] = []  # filename + text preview for combined analysis
    processing_errors = []  # Track errors for debugging

    for file in files:
        filename_lower = file.filename.lower()
        if not filename_lower.endswith(('.pdf', '.docx', '.csv', '.xlsx')):
            processing_errors.append(f"Unsupported file type: {file.filename}")
            continue

        suffix = Path(file.filename).suffix or '.dat'
        tmp_path = None
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                # Copy file content to temp file
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            
            # Extract text from the file
            text = extract_text_by_extension(tmp_path, filename_lower)
            
            # Check if text extraction was successful
            if not text or not text.strip():
                error_msg = f"Could not extract text from {file.filename}"
                if text == "Could not extract text from PDF - file may be corrupted, password-protected, or contain only images":
                    error_msg = f"PDF text extraction failed for {file.filename}"
                elif text == "Document appears to be empty or contains no extractable text":
                    error_msg = f"DOCX text extraction failed for {file.filename}"
                elif text == "CSV file appears to be empty or contains no data":
                    error_msg = f"CSV text extraction failed for {file.filename}"
                elif text == "Excel file appears to be empty or contains no data":
                    error_msg = f"XLSX text extraction failed for {file.filename}"
                elif text == "":
                    error_msg = f"No text content found in {file.filename}"
                processing_errors.append(error_msg)
                continue

            # Analyze with AI
            analysis = analyze_with_ai(text, file.filename)
            
            # Check if AI analysis failed
            if "error" in analysis.get("ai_analysis", "").lower():
                processing_errors.append(f"AI analysis failed for {file.filename}: {analysis['ai_analysis']}")
                continue

            doc_id = str(uuid.uuid4())
            result = {
                "document_id": doc_id,
                "filename": file.filename,
                "document_type": analysis["document_type"],
                "processed_at": datetime.now().isoformat(),
                "summary": {
                    "total_transactions": 0,
                    "total_amount": 0.0,
                    "date_range": {},
                    "key_insights": [analysis["ai_analysis"][:300]]
                },
                "transactions": [],
                "anomalies": [],
                "risk_score": analysis["risk_score"],
                "recommendations": ["Review the AI analysis for insights"],
                "extractable_data": {"text_preview": text[:300]}
            }

            documents[doc_id] = {
                "result": result,
                "full_text": text,
                "ai_analysis": analysis["ai_analysis"]
            }

            # Save to database
            try:
                save_document(
                    document_id=doc_id,
                    filename=file.filename,
                    document_type=analysis["document_type"],
                    content=text,
                    analysis_result=result,
                    session_id=session_id,
                    db=db
                )
                if thread_id:
                    save_document_to_thread(thread_id=thread_id, document_id=doc_id, session_id=session_id, db=db)
            except Exception as e:
                print(f"Database save error for {file.filename}: {e}")
                # Continue processing even if DB save fails
            
            results.append(result)
            previews.append({
                "filename": file.filename,
                "preview": text[:1500]
            })
            
            print(f"Successfully processed {file.filename}")
            
        except Exception as e:
            error_msg = f"Error processing {file.filename}: {str(e)}"
            processing_errors.append(error_msg)
            print(error_msg)
        finally:
            # Clean up temporary file
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    try:
                        import time
                        time.sleep(0.1)
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Failed to clean up temp file {tmp_path}: {e}")

    if not results:
        error_detail = "No valid documents processed. "
        if processing_errors:
            error_detail += f"Errors: {'; '.join(processing_errors[:3])}"  # Show first 3 errors
        else:
            error_detail += "All files failed processing."
        raise HTTPException(status_code=400, detail=error_detail)

    # Build combined insights using LLM if configured
    combined = {
        "key_insights": [],
        "risk_score": 0.0,
        "recommendations": []
    }

    try:
        if model:
            combined_prompt = (
                "Hey! I'm your friendly financial assistant. I'm looking at multiple financial documents together to give you a helpful overview.\n\n"
            )
            for p in previews:
                combined_prompt += f"Document: {p['filename']}\nContent Preview: {p['preview']}\n\n"
            combined_prompt += (
                "Can you help me provide:\n"
                "1) 4-7 consolidated Key Insights in a friendly, conversational tone\n"
                "2) An overall Risk Score from 0-10 (where 0 = no worries, 10 = needs attention)\n"
                "3) 3-5 actionable Recommendations in a helpful, friendly way\n"
                "\nKeep it warm and conversational, like you're helping a friend understand their finances!"
            )

            combined_response = model.generate_content(combined_prompt)
            text_out = combined_response.text or ""

            # Extract risk score
            import re as _re
            risk_score = 0.0
            m = _re.search(r"risk\s*score\D*(\d+(?:\.\d+)?)", text_out, _re.IGNORECASE)
            if m:
                try:
                    risk_score = float(m.group(1))
                    risk_score = max(0.0, min(10.0, risk_score))
                except Exception:
                    risk_score = 0.0

            # Extract bullet lists
            insights = []
            recs = []
            bullets = [line.strip(" -*•\t").strip() for line in text_out.splitlines() if line.strip().startswith(("-","*","•"))]
            # Heuristic: first half bullets as insights, latter as recs if headings not present
            if bullets:
                split_at = max(2, len(bullets)//2)
                insights = bullets[:split_at]
                recs = bullets[split_at:]

            combined["key_insights"] = insights or [r["summary"]["key_insights"][0] for r in results if r["summary"]["key_insights"]][:5]
            combined["risk_score"] = risk_score or (sum(r["risk_score"] for r in results) / len(results))
            combined["recommendations"] = recs or ["Review combined financial patterns across documents", "Pay extra attention to high-risk areas highlighted"]
        else:
            # Fallback without LLM
            combined["key_insights"] = [r["summary"]["key_insights"][0] for r in results if r["summary"]["key_insights"]][:5]
            combined["risk_score"] = sum(r["risk_score"] for r in results) / len(results)
            combined["recommendations"] = ["Monitor for unusual patterns across all documents", "Validate large or frequent transactions"]
    except Exception as e:
        print(f"Error in combined analysis: {e}")
        combined["key_insights"] = [r["summary"]["key_insights"][0] for r in results if r["summary"]["key_insights"]][:5]
        combined["risk_score"] = sum(r["risk_score"] for r in results) / len(results)
        combined["recommendations"] = ["Review combined results manually"]

    return {"results": results, "combined": combined}

@app.post("/chat")
async def chat(
    request: Dict[str, Any],
    request_obj: Request = None,
    db: Session = Depends(get_db)
):
    """Chat about document"""
    
    doc_id = request.get("document_id")
    question = request.get("question")
    session_id = get_session_id(request_obj)
    
    if not doc_id or doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = documents[doc_id]
    
    try:
        if not model:
            # Friendly fallback when LLM is not available
            return {
                "answer": "Hi there! 👋 I'd love to chat about your document, but I need my AI brain (Gemini API) to be configured first. Please add your GEMINI_API_KEY to the .env file and I'll be happy to help answer your questions!",
                "document_id": doc_id
            }
        
        prompt = f"""
        Hey! I'm your friendly financial assistant. I'm looking at this document: {doc_data['result']['filename']}

        Here's what I can see in it: {doc_data['full_text'][:2000]}

        The user asked: {question}

        Can you help me give them a friendly, helpful answer? Keep it conversational and warm, like you're talking to a friend about their finances. If the information isn't in the document, just let them know nicely!
        """
        
        response = model.generate_content(prompt)
        answer = response.text
        
        # Save conversation to database
        try:
            save_conversation(
                question=question,
                answer=answer,
                document_id=doc_id,
                session_id=session_id,
                db=db
            )
        except Exception as e:
            print(f"Database save error: {e}")
        
        return {
            "answer": answer,
            "document_id": doc_id
        }
    
    except Exception as e:
        return {
            "answer": f"Hey there! 😅 I ran into a little issue while trying to answer your question: {str(e)}. Don't worry though - you can still view your document!",
            "document_id": doc_id
        }

@app.post("/chat-multi")
async def chat_multi(request: Dict[str, Any]):
    """Ask a question across multiple analyzed documents"""
    document_ids: List[str] = request.get("document_ids", [])
    question: str = request.get("question", "")

    if not document_ids:
        raise HTTPException(status_code=400, detail="document_ids is required")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    # Build combined context with truncation
    contexts = []
    total_budget = 3000  # chars budget
    per_doc_budget = max(400, total_budget // max(1, len(document_ids)))

    for doc_id in document_ids:
        if doc_id not in documents:
            continue
        doc = documents[doc_id]
        name = doc["result"]["filename"]
        content = (doc["full_text"] or "")[:per_doc_budget]
        contexts.append(f"Document: {name}\nContent: {content}\n")

    if not contexts:
        raise HTTPException(status_code=404, detail="No documents found")

    try:
        if not model:
            return {
                "answer": "Hi there! 👋 I'd love to analyze your documents together, but I need my AI brain (Gemini API) to be configured first. Please add your GEMINI_API_KEY to the .env file and I'll be happy to help!",
                "document_ids": document_ids
            }

        prompt = (
            "Hey! I'm your friendly financial assistant. I'm looking at multiple documents together to answer your question.\n\n" +
            "\n\n".join(contexts) +
            f"\nThe user asked: {question}\n\nCan you give them a friendly, helpful answer that references the specific documents when relevant? Keep it conversational and warm!"
        )

        response = model.generate_content(prompt)
        return {"answer": response.text, "document_ids": document_ids}
    except Exception as e:
        return {"answer": f"Hey there! 😅 I ran into a little issue while trying to analyze your documents together: {str(e)}. Don't worry though - you can still view your documents individually!", "document_ids": document_ids}

@app.get("/documents")
async def get_documents():
    """List documents"""
    doc_list = []
    for doc_id, doc_data in documents.items():
        result = doc_data["result"]
        doc_list.append({
            "document_id": doc_id,
            "filename": result["filename"],
            "document_type": result["document_type"],
            "risk_score": result["risk_score"],
            "transaction_count": 0,
            "anomaly_count": 0
        })
    
    return {"documents": doc_list}

@app.get("/conversations")
async def get_conversations(
    request: Request = None,
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get conversation history for the current session"""
    session_id = get_session_id(request)
    conversations = get_user_conversations(session_id, db, limit)
    return {"conversations": conversations}

@app.get("/user-documents")
async def get_user_documents_endpoint(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all documents for the current session"""
    session_id = get_session_id(request)
    documents_list = get_user_documents(session_id, db)
    return {"documents": documents_list}

@app.delete("/documents/{document_id}")
async def delete_document_endpoint(
    document_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Delete a document and all its conversations"""
    session_id = get_session_id(request)
    success = delete_document(document_id, session_id, db)
    if success:
        # Also remove from in-memory storage
        if document_id in documents:
            del documents[document_id]
        return {"message": "Document deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Document not found")

# Conversation Thread Endpoints
@app.post("/threads")
async def create_thread(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Create a new conversation thread"""
    session_id = get_session_id(request)
    thread = create_conversation_thread(session_id, db=db)
    return {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "created_at": thread.created_at.isoformat()
    }

@app.get("/threads")
async def get_threads(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all conversation threads for the current user"""
    session_id = get_session_id(request)
    threads = get_user_threads(session_id, db=db)
    return {"threads": threads}

@app.get("/threads/{thread_id}/messages")
async def get_messages(
    thread_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all messages in a conversation thread"""
    session_id = get_session_id(request)
    messages = get_thread_messages(thread_id, session_id, db=db)
    return {"messages": messages}

@app.get("/threads/{thread_id}/documents")
async def get_thread_docs(
    thread_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all documents associated with a conversation thread for current user"""
    session_id = get_session_id(request)
    docs = get_thread_documents(thread_id, session_id, db=db)
    return {"documents": docs}

@app.post("/threads/{thread_id}/messages")
async def add_message(
    thread_id: str,
    request: Dict[str, Any],
    request_obj: Request = None,
    db: Session = Depends(get_db)
):
    """Add a message to a conversation thread"""
    session_id = get_session_id(request_obj)
    role = request.get("role", "user")
    content = request.get("content", "")
    document_id = request.get("document_id")
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    
    message = add_message_to_thread(
        thread_id=thread_id,
        role=role,
        content=content,
        session_id=session_id,
        document_id=document_id,
        db=db
    )
    
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "timestamp": message.timestamp.isoformat()
    }

@app.post("/threads/{thread_id}/chat")
async def chat_in_thread(
    thread_id: str,
    request: Dict[str, Any],
    request_obj: Request = None,
    db: Session = Depends(get_db)
):
    """Chat in a specific thread with AI response"""
    session_id = get_session_id(request_obj)
    user_message = request.get("message", "")
    document_ids = request.get("document_ids", [])
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Add user message to thread
    add_message_to_thread(
        thread_id=thread_id,
        role="user",
        content=user_message,
        session_id=session_id,
        db=db
    )
    
    # Check for simple greetings first (LLM-free responses)
    user_message_lower = user_message.lower().strip()
    simple_greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "howdy", "sup", "yo"]
    
    if any(greeting in user_message_lower for greeting in simple_greetings):
        ai_response = "Hello there! 👋 I'm your friendly FinanceBot assistant! I'm here to help you analyze your financial documents and answer any questions you might have. Feel free to upload some documents or ask me anything about your finances!"
    elif "how are you" in user_message_lower or "how are you doing" in user_message_lower:
        ai_response = "I'm doing great, thanks for asking! 😊 I'm excited to help you with your financial documents. What would you like to work on today?"
    elif "thank" in user_message_lower or "thanks" in user_message_lower:
        ai_response = "You're very welcome! 😊 I'm happy to help. Is there anything else you'd like to know about your financial documents?"
    elif "bye" in user_message_lower or "goodbye" in user_message_lower or "see you" in user_message_lower:
        ai_response = "Goodbye! 👋 It was great chatting with you. Feel free to come back anytime if you have more questions about your finances!"
    else:
        # Generate AI response for other messages
        try:
            if not model:
                ai_response = "Hi there! 👋 I'd love to chat with you, but I need my AI brain (Gemini API) to be configured first. Please add your GEMINI_API_KEY to the .env file and I'll be happy to help answer your questions!"
            else:
                # Build context from documents if provided
                context = ""
                if document_ids:
                    contexts = []
                    for doc_id in document_ids:
                        if doc_id in documents:
                            doc = documents[doc_id]
                            contexts.append(f"Document: {doc['result']['filename']}\nContent: {doc['full_text'][:1000]}")
                    if contexts:
                        context = "\n\n".join(contexts) + "\n\n"
                
                prompt = f"""
                Hey! I'm your friendly financial assistant. {context}The user just said: {user_message}

                Can you give them a friendly, helpful response? Keep it conversational and warm, like you're talking to a friend. If they have documents uploaded, feel free to reference them in your answer!
                """
                
                response = model.generate_content(prompt)
                ai_response = response.text
        except Exception as e:
            ai_response = f"Hey there! 😅 I ran into a little issue while trying to respond: {str(e)}. Don't worry though - I'm here to help once we get this sorted out!"
    
    # Add AI response to thread
    add_message_to_thread(
        thread_id=thread_id,
        role="assistant",
        content=ai_response,
        session_id=session_id,
        db=db
    )
    
    return {
        "response": ai_response,
        "thread_id": thread_id
    }

@app.delete("/threads/{thread_id}")
async def delete_thread_endpoint(
    thread_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Delete a conversation thread"""
    session_id = get_session_id(request)
    success = delete_thread(thread_id, session_id, db=db)
    if success:
        return {"message": "Thread deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Thread not found")

@app.get("/health")
async def health():
    """Health check endpoint"""
    gemini_status = "not_configured"
    gemini_error = None
    
    if model:
        try:
            # Test the model with a simple prompt
            test_response = model.generate_content("Hello")
            if test_response and test_response.text:
                gemini_status = "working"
            else:
                gemini_status = "responding_but_empty"
        except Exception as e:
            gemini_status = "error"
            gemini_error = str(e)
    else:
        gemini_error = "No GEMINI_API_KEY found in environment variables"
    
    return {
        "status": "healthy",
        "message": "🚀 FinanceBot is running and ready to help!",
        "timestamp": datetime.now().isoformat(),
        "gemini": {
            "status": gemini_status,
            "configured": bool(model),
            "error": gemini_error,
            "note": "Gemini API is FREE to use! Get your key at https://makersuite.google.com/app/apikey"
        },
        "database": "connected",  # Assuming database is working if we reach this point
        "features": {
            "document_analysis": "ready",
            "chat": "ready" if model else "needs_gemini_api_key",
            "file_support": ["PDF", "DOCX", "CSV", "XLSX"]
        }
    }

if __name__ == "__main__":
    print("🚀 Starting FinanceBot with Google Gemini...")
    print("📊 Backend API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🔑 Make sure to set GEMINI_API_KEY in .env file")
    print("🆓 Gemini is FREE to use!")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
