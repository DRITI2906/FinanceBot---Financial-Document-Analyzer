# Finance GenAI Chatbot

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
- **OpenAI GPT-4**: Primary language model
- **Claude (optional)**: Alternative AI provider
- **ChromaDB**: Vector database for document embeddings
- **Sentence Transformers**: Text embeddings

## 📋 Prerequisites

Before running the application, ensure you have:

- **Python 3.8+** installed
- **Node.js 16+** and npm installed
- **OpenAI API Key** (required for AI features)
- **Tesseract OCR** installed for image processing

### Install Tesseract OCR

**Windows:**
```bash
# Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
# Or using chocolatey:
choco install tesseract
```

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd Finance-Genai-Chatbot
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 3. Configure Environment

Edit `backend/.env` file with your settings:

```env
# Required - OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Alternative AI providers
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional - LangSmith monitoring
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=finance-genai-chatbot

# Database (SQLite by default)
DATABASE_URL=sqlite:///./finance_chatbot.db

# Application settings
MAX_FILE_SIZE=52428800  # 50MB
HIGH_RISK_TRANSACTION_AMOUNT=100000  # ₹1L
FRAUD_DETECTION_ENABLED=true
```

### 4. Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install dependencies
npm install

# Note: If you encounter dependency issues, try:
npm install --legacy-peer-deps
```

### 5. Run the Application

#### Option 1: Run Both Services Separately

**Terminal 1 - Backend:**
```bash
cd backend
# Activate virtual environment if not already active
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

#### Option 2: Using the Startup Scripts

**Windows - Create `start.bat`:**
```batch
@echo off
echo Starting Finance GenAI Chatbot...

echo Starting Backend...
start "Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 5

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm start"

echo Both services started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
```

**macOS/Linux - Create `start.sh`:**
```bash
#!/bin/bash
echo "Starting Finance GenAI Chatbot..."

echo "Starting Backend..."
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 5

echo "Starting Frontend..."
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "Both services started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Keep script running
wait
```

### 6. Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

## 📖 Usage Guide

### Upload and Analyze Documents

1. **Navigate** to http://localhost:3000
2. **Upload** a financial document (PDF, PNG, JPG)
3. **Wait** for AI analysis to complete
4. **Review** the analysis results including:
   - Document summary and statistics
   - Transaction details
   - Detected anomalies and risk factors
   - AI-generated recommendations

### Chat with Your Documents

1. **Go to** the Analysis page for any processed document
2. **Click** on the "Ask AI" tab
3. **Ask questions** like:
   - "What are the top 5 largest transactions?"
   - "Are there any suspicious patterns?"
   - "How much was spent on travel?"
   - "What transactions happened after 10 PM?"

### Manage Documents

- **View all** processed documents in the Documents page
- **Filter** by risk level or search by filename
- **Compare** risk scores and anomaly counts
- **Re-analyze** documents by clicking "View Analysis"

## 🎯 Supported Document Types

### Bank Statements
- **Detection**: Opening/closing balances, transaction patterns
- **Anomalies**: Overdrafts, unusual amounts, suspicious timing
- **Insights**: Spending patterns, balance trends

### Invoices
- **Detection**: Payment terms, due dates, amounts
- **Anomalies**: Overdue payments, duplicate invoices
- **Insights**: Vendor analysis, payment patterns

### Annual Reports
- **Detection**: Financial statements, KPIs
- **Anomalies**: High debt ratios, negative cash flow
- **Insights**: Financial health indicators

### Transaction Histories
- **Detection**: Individual transactions, patterns
- **Anomalies**: Round number patterns, foreign transactions
- **Insights**: Spending categories, frequency analysis

## 🔧 Configuration

### Risk Analysis Settings

Customize risk detection in `backend/.env`:

```env
# Transaction amount threshold for high-risk flagging
HIGH_RISK_TRANSACTION_AMOUNT=100000

# Enable/disable fraud detection features
FRAUD_DETECTION_ENABLED=true

# File upload limits
MAX_FILE_SIZE=52428800  # 50MB
```

### AI Model Configuration

```env
# Primary LLM model
DEFAULT_LLM=gpt-4

# Model temperature (0.0 - 1.0)
TEMPERATURE=0.1

# Alternative models
# DEFAULT_LLM=claude-3-sonnet-20240229
# DEFAULT_LLM=gpt-3.5-turbo
```

## 🐛 Troubleshooting

### Common Issues

#### Frontend Won't Start
```bash
# Clear npm cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

#### Backend API Errors
```bash
# Check Python virtual environment
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

#### OCR Not Working
```bash
# Verify tesseract installation
tesseract --version

# If not found, install tesseract OCR
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

#### API Key Issues
- Ensure your OpenAI API key is valid and has sufficient credits
- Check the `.env` file format (no quotes around the key)
- Verify the key has GPT-4 access if using that model

### Performance Optimization

#### For Large Documents
- Increase file size limits in `.env`
- Consider using GPT-3.5-turbo for faster processing
- Enable document chunking for very large files

#### For High Volume
- Use a production database (PostgreSQL/MySQL) instead of SQLite
- Implement Redis for caching
- Consider deploying with Gunicorn/Docker

## 🚀 Production Deployment

### Docker Deployment

**Backend Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:16-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
EXPOSE 80
```

### Environment Variables for Production

```env
# Production settings
DATABASE_URL=postgresql://user:pass@localhost/finance_db
REDIS_URL=redis://localhost:6379
DEBUG=false

# Security
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com
```

## 📝 API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

### Key Endpoints

- `POST /upload` - Upload and analyze document
- `POST /chat` - Chat with analyzed document
- `GET /documents` - List all processed documents
- `GET /health` - Health check

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information

---

## 🎉 What's Next?

This Finance GenAI Chatbot provides a solid foundation for financial document analysis. You can extend it with:

- **Additional AI Models**: Integrate more LLMs for specialized tasks
- **Advanced Analytics**: Add time-series analysis and forecasting
- **API Integrations**: Connect to banking APIs or financial data providers
- **Mobile App**: Create a React Native mobile version
- **Enterprise Features**: Add user management, audit trails, and compliance reporting

Happy analyzing! 📊💰
