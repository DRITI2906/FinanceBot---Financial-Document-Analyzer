from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import List, Dict, Any
import tempfile
import shutil
from pathlib import Path

from src.document_processor import DocumentProcessor
from src.langraph_workflow import FinancialAnalysisWorkflow
from src.models import AnalysisResult, ChatQuery, ChatResponse
from src.config import get_settings

# Initialize FastAPI app
app = FastAPI(
    title="Finance GenAI Chatbot",
    description="AI-powered financial document analysis and chatbot",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
settings = get_settings()
document_processor = DocumentProcessor()
workflow = FinancialAnalysisWorkflow()

@app.get("/")
async def root():
    return {"message": "Finance GenAI Chatbot API", "version": "1.0.0"}

@app.post("/upload", response_model=AnalysisResult)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and analyze a financial document
    """
    if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF and image files are supported"
        )
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        # Process document through LangGraph workflow
        result = await workflow.process_document(tmp_path, file.filename)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_document(query: ChatQuery):
    """
    Chat with the analyzed document for insights
    """
    try:
        response = await workflow.chat_query(query.document_id, query.question)
        return ChatResponse(answer=response, document_id=query.document_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/documents")
async def list_documents():
    """
    Get list of processed documents
    """
    try:
        documents = await workflow.get_processed_documents()
        return {"documents": documents}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
