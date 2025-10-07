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

## Deployment

This project has a React frontend (`frontend/`) and a FastAPI backend (`backend/`).

Recommended production setup in this guide:

- Deploy the frontend to Vercel (static build).
- Deploy the backend to Render as a web service (runs Uvicorn/Gunicorn).

### Environment variables

The backend expects these environment variables (see `backend/.env.example`):

- GEMINI_API_KEY - your Google Generative AI (Gemini) API key.
- FRONTEND_URL - allowed origins for CORS (e.g. https://your-vercel-app.vercel.app)
- DATABASE_URL - optional; if empty the app uses a local SQLite file. For Render use a managed Postgres and set DATABASE_URL.
- PORT - optional web port (Render sets this automatically).

### Frontend -> Vercel

1. In the `frontend/` folder this is a standard Create React App. It already has `build` and `start` scripts in `package.json`.
2. Create a new project on Vercel and point it to this repo (or the `frontend` folder if you want to deploy only the frontend).
3. Set the following Environment Variable for the Vercel project:
	- REACT_APP_API_URL = https://<your-backend-host>
4. Build & deploy. Vercel will run `npm run build` and serve the static files.

Notes: `frontend/vercel.json` is included to ensure a static build deployment.

### Backend -> Render

1. Create a new Web Service on Render (or use the free plan for testing).
2. Connect your repo, and set the root directory to `backend/`.
3. Set the build command to: `pip install -r requirements.txt`
4. Set the start command to: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render (GEMINI_API_KEY, DATABASE_URL if using Postgres, FRONTEND_URL to your Vercel domain).
6. If you use Postgres on Render, set `DATABASE_URL` to the provided connection string.

Optional: Use a `Dockerfile` or `render.yaml` for more control (not required).

### Local testing

Backend (from `backend/`):

```powershell
cd backend
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set GEMINI_API_KEY
python main.py
```

Frontend (from `frontend/`):

```powershell
cd frontend
npm install
npm run build
# or for dev:
npm start
```

### Verification

- Visit the Vercel frontend URL and try uploading a small PDF.
- Check Render backend logs and the `/health` endpoint: `https://<your-backend>/health`

If you want, I can add a `render.yaml` and a simple `Dockerfile` and test a local backend start as the next step.