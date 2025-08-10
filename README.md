# FinanceBot

A comprehensive AI-powered financial document analysis system that uses LangGraph workflows to analyze financial documents, detect anomalies, and provide intelligent insights through a modern React interface.

## 🚀 Features

### Core Functionality
- **Smart Document Parsing**: Extract data from PDFs and images using advanced OCR and AI
- **LangGraph Workflow**: File Upload → Parsing → Summary → Highlight Anomalies
- **Multi-format Support**: Bank statements, invoices, annual reports, transaction histories

### AI-Powered Analysis
- **Fraud Detection**: Detect multiple small transactions, unusual timings, foreign transactions
- **Anomaly Detection**: Flag suspicious patterns, duplicates, and high-risk transactions
- **Risk Scoring**: Comprehensive risk assessment with actionable recommendations
- **Intelligent Chat**: Ask questions about your documents using natural language

### Advanced Features
- **Searchable Insights**: Query documents with questions like "How much was spent on travel?"
- **Risk Assessment**: Financial risk ratings with benchmark comparisons
- **Custom Rules**: Define rules like "Flag transactions over ₹1L to non-domestic accounts"
- **Multi-document Comparison**: Review trends across months/years
- **Data Export**: CSV or Excel outputs of key data

## 🛠️ Tech Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **LangGraph**: Orchestration of AI workflows
- **LangChain**: LLM integration and document processing
- **PyMuPDF + pdfplumber**: PDF parsing and text extraction
- **pytesseract**: OCR for scanned documents
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation and settings

### Frontend
- **React 18**: Modern React with TypeScript
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Smooth animations and transitions
- **React Router**: Client-side routing
- **Axios**: HTTP client for API calls
- **React Dropzone**: File upload interface
- **Recharts**: Data visualization
- **React Hot Toast**: User notifications

### AI/ML Stack
- **Gemini**: Primary language model
- **Claude (optional)**: Alternative AI provider
- **ChromaDB**: Vector database for document embeddings
- **Sentence Transformers**: Text embeddings