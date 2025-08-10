from fastapi import FastAPI, File, UploadFile, HTTPException
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

def extract_docx_text(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""

def extract_csv_text(file_path: str) -> str:
    try:
        lines = []
        with open(file_path, newline='', encoding='utf-8', errors='ignore') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                lines.append(", ".join(cell.strip() for cell in row))
        return "\n".join(lines)
    except Exception:
        return ""

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
        return "\n".join(lines)
    except Exception:
        return ""
    finally:
        try:
            if wb is not None:
                wb.close()
        except Exception:
            pass

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
async def upload_file(file: UploadFile = File(...)):
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
        
        # Store document
        documents[doc_id] = {
            "result": result,
            "full_text": text,
            "ai_analysis": analysis["ai_analysis"]
        }
        
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
async def upload_multiple(files: List[UploadFile] = File(...)):
    """Upload and analyze multiple documents (pdf, docx, csv, xlsx)"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results: List[Dict[str, Any]] = []
    previews: List[Dict[str, str]] = []  # filename + text preview for combined analysis

    for file in files:
        filename_lower = file.filename.lower()
        if not filename_lower.endswith(('.pdf', '.docx', '.csv', '.xlsx')):
            # Skip unsupported
            continue

        suffix = Path(file.filename).suffix or '.dat'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            text = extract_text_by_extension(tmp_path, filename_lower)
            if not text.strip():
                continue

            analysis = analyze_with_ai(text, file.filename)

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

            results.append(result)
            previews.append({
                "filename": file.filename,
                "preview": text[:1500]
            })
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

    if not results:
        raise HTTPException(status_code=400, detail="No valid documents processed")

    # Build combined insights using LLM if configured
    combined = {
        "key_insights": [],
        "risk_score": 0.0,
        "recommendations": []
    }

    try:
        if model:
            combined_prompt = (
                "You are a financial analyst. Analyze these multiple financial documents together and provide a consolidated summary.\n\n"
            )
            for p in previews:
                combined_prompt += f"Document: {p['filename']}\nContent Preview: {p['preview']}\n\n"
            combined_prompt += (
                "Provide:\n"
                "1) 4-7 consolidated Key Insights (bulleted).\n"
                "2) An overall Risk Score from 0-10.\n"
                "3) 3-5 actionable Recommendations (bulleted).\n"
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
    except Exception:
        combined["key_insights"] = [r["summary"]["key_insights"][0] for r in results if r["summary"]["key_insights"]][:5]
        combined["risk_score"] = sum(r["risk_score"] for r in results) / len(results)
        combined["recommendations"] = ["Review combined results manually"]

    return {"results": results, "combined": combined}

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
                "answer": "Gemini API key not configured. Please add GEMINI_API_KEY to .env file",
                "document_ids": document_ids
            }

        prompt = (
            "You are a financial analyst. Answer the user's question using ALL documents below.\n\n" +
            "\n\n".join(contexts) +
            f"\nUser Question: {question}\n\nProvide a consolidated answer that references specific documents when relevant."
        )

        response = model.generate_content(prompt)
        return {"answer": response.text, "document_ids": document_ids}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "document_ids": document_ids}

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
