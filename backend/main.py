from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime
import pdfplumber
import PyPDF2
import google.generativeai as genai
from dotenv import load_dotenv
import uuid
import re

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

# Simple in-memory storage
documents = {}

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
    except:
        pass
    
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except:
        pass
    
    return text or "Could not extract text from PDF"

def analyze_with_ai(text: str, filename: str) -> Dict[str, Any]:
    """Get AI analysis using Google Gemini"""
    try:
        if not model:
            return {
                "ai_analysis": "Gemini API key not configured. Please add GEMINI_API_KEY to .env file",
                "risk_score": 0.0,
                "document_type": "unknown"
            }
        
        prompt = f"""
        As a financial analyst, analyze this financial document and provide detailed insights:

        Document Name: {filename}
        Document Content: {text[:3000]}

        Please provide:
        1. Document Type (bank_statement, invoice, annual_report, transaction_history, or other)
        2. Key Financial Insights (3-5 bullet points)
        3. Risk Assessment Score (0-10, where 0=no risk, 10=very high risk)
        4. Any Suspicious Patterns or Anomalies
        5. Actionable Recommendations

        Format your response clearly with sections for each point.
        """
        
        response = model.generate_content(prompt)
        ai_response = response.text
        
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
        return {
            "ai_analysis": f"Gemini analysis error: {str(e)}. Please check your GEMINI_API_KEY.",
            "risk_score": 0.0,
            "document_type": "unknown"
        }

@app.get("/")
async def root():
    return {
        "message": "FinanceBot API with Google Gemini",
        "status": "running",
        "gemini_configured": bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')),
        "model": "gemini-pro"
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and analyze document"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        # Extract text
        text = extract_pdf_text(tmp_path)
        
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
                "key_insights": [analysis["ai_analysis"][:200] + "..."]
            },
            "transactions": [],
            "anomalies": [],
            "risk_score": analysis["risk_score"],
            "recommendations": ["Review the AI analysis for insights"],
            "extractable_data": {"text_preview": text[:300]}
        }
        
        # Store document
        documents[doc_id] = {
            "result": result,
            "full_text": text,
            "ai_analysis": analysis["ai_analysis"]
        }
        
        return result
        
    finally:
        os.unlink(tmp_path)

@app.post("/chat")
async def chat(request: Dict[str, Any]):
    """Chat about document"""
    
    doc_id = request.get("document_id")
    question = request.get("question")
    
    if not doc_id or doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = documents[doc_id]
    
    try:
        if not model:
            return {
                "answer": "Gemini API key not configured. Please add GEMINI_API_KEY to .env file",
                "document_id": doc_id
            }
        
        prompt = f"""
        Based on this financial document, please answer the user's question:

        Document: {doc_data['result']['filename']}
        Content: {doc_data['full_text'][:2000]}

        User Question: {question}

        Please provide a helpful, specific answer based on the document content. If the information isn't available in the document, say so clearly.
        """
        
        response = model.generate_content(prompt)
        
        return {
            "answer": response.text,
            "document_id": doc_id
        }
        
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "document_id": doc_id
        }

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

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "gemini_configured": bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')),
        "model": "gemini-pro",
        "documents_count": len(documents)
    }

if __name__ == "__main__":
    print("🚀 Starting FinanceBot with Google Gemini...")
    print("📊 Backend API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🔑 Make sure to set GEMINI_API_KEY in .env file")
    print("🆓 Gemini is FREE to use!")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
