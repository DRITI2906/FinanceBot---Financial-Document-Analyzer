export interface Transaction {
  date: string;
  description: string;
  amount: number;
  category?: string;
  account?: string;
  balance?: number;
}

export interface Anomaly {
  type: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  details: Record<string, any>;
}

export interface Summary {
  total_transactions: number;
  total_amount: number;
  date_range: Record<string, string>;
  top_categories: Array<Record<string, any>>;
  account_balances: Array<Record<string, any>>;
  key_insights: string[];
}

export interface AnalysisResult {
  document_id: string;
  filename: string;
  document_type: 'bank_statement' | 'invoice' | 'annual_report' | 'transaction_history' | 'other';
  processed_at: string;
  summary: Summary;
  transactions: Transaction[];
  anomalies: Anomaly[];
  risk_score: number;
  recommendations: string[];
  extractable_data: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  question: string;
  answer: string;
  timestamp: string;
  document_id: string;
}

export interface ProcessedDocument {
  document_id: string;
  filename: string;
  document_type: string;
  risk_score: number;
  transaction_count: number;
  anomaly_count: number;
}
