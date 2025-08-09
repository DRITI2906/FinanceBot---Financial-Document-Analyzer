from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    BANK_STATEMENT = "bank_statement"
    INVOICE = "invoice"
    ANNUAL_REPORT = "annual_report"
    TRANSACTION_HISTORY = "transaction_history"
    OTHER = "other"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Transaction(BaseModel):
    date: str
    description: str
    amount: float
    category: Optional[str] = None
    account: Optional[str] = None
    balance: Optional[float] = None

class Anomaly(BaseModel):
    type: str
    description: str
    risk_level: RiskLevel
    confidence: float
    details: Dict[str, Any]

class Summary(BaseModel):
    total_transactions: int
    total_amount: float
    date_range: Dict[str, str]
    top_categories: List[Dict[str, Any]]
    account_balances: List[Dict[str, Any]]
    key_insights: List[str]

class AnalysisResult(BaseModel):
    document_id: str
    filename: str
    document_type: DocumentType
    processed_at: datetime
    summary: Summary
    transactions: List[Transaction]
    anomalies: List[Anomaly]
    risk_score: float
    recommendations: List[str]
    extractable_data: Dict[str, Any]

class ChatQuery(BaseModel):
    document_id: str
    question: str

class ChatResponse(BaseModel):
    answer: str
    document_id: str
    relevant_data: Optional[Dict[str, Any]] = None
