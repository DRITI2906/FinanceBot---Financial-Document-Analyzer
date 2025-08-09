import pdfplumber
import PyPDF2
import pandas as pd
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path
import logging
from datetime import datetime

from .models import Transaction, DocumentType

class DocumentProcessor:
    """
    Handles document parsing and text extraction from various financial documents
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def process_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Main processing function that extracts text and structured data from documents
        """
        file_extension = Path(filename).suffix.lower()
        
        if file_extension == '.pdf':
            return await self._process_pdf(file_path, filename)
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            return await self._process_image(file_path, filename)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    async def _process_pdf(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process PDF documents using multiple methods"""
        
        # Try pdfplumber first (better for structured data)
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                tables = []
                
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                # If no text found, fall back to OCR
                if not text.strip():
                    text = await self._ocr_pdf(file_path)
                
                return {
                    "text": text,
                    "tables": tables,
                    "method": "pdfplumber" if text.strip() else "ocr",
                    "document_type": self._detect_document_type(text, filename)
                }
        
        except Exception as e:
            self.logger.warning(f"pdfplumber failed: {e}, trying OCR")
            text = await self._ocr_pdf(file_path)
            return {
                "text": text,
                "tables": [],
                "method": "ocr",
                "document_type": self._detect_document_type(text, filename)
            }
    
    async def _process_image(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process image documents - simplified for now"""
        
        # For now, return a message about image processing
        text = "Image processing requires OCR setup. Please convert to PDF or use text-based documents."
        return {
            "text": text,
            "tables": [],
            "method": "basic",
            "document_type": self._detect_document_type(text, filename)
        }
    
    async def _ocr_pdf(self, file_path: str) -> str:
        """Fallback PDF text extraction using PyPDF2"""
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text
        
        except Exception as e:
            raise ValueError(f"PDF text extraction failed: {e}")
    
    def _detect_document_type(self, text: str, filename: str) -> DocumentType:
        """Detect the type of financial document based on content"""
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Bank statement indicators
        bank_keywords = ['account number', 'opening balance', 'closing balance', 
                        'transaction', 'debit', 'credit', 'bank statement']
        
        # Invoice indicators
        invoice_keywords = ['invoice', 'bill', 'due date', 'amount due', 
                           'payment terms', 'tax id']
        
        # Annual report indicators
        report_keywords = ['annual report', 'financial statement', 'balance sheet',
                          'income statement', 'cash flow', 'assets', 'liabilities']
        
        # Check filename first
        if any(keyword in filename_lower for keyword in ['statement', 'bank']):
            return DocumentType.BANK_STATEMENT
        elif any(keyword in filename_lower for keyword in ['invoice', 'bill']):
            return DocumentType.INVOICE
        elif any(keyword in filename_lower for keyword in ['report', 'annual']):
            return DocumentType.ANNUAL_REPORT
        
        # Check content
        bank_score = sum(1 for keyword in bank_keywords if keyword in text_lower)
        invoice_score = sum(1 for keyword in invoice_keywords if keyword in text_lower)
        report_score = sum(1 for keyword in report_keywords if keyword in text_lower)
        
        if bank_score >= 3:
            return DocumentType.BANK_STATEMENT
        elif invoice_score >= 2:
            return DocumentType.INVOICE
        elif report_score >= 2:
            return DocumentType.ANNUAL_REPORT
        else:
            return DocumentType.OTHER
    
    def extract_transactions(self, text: str, tables: List[List[List[str]]]) -> List[Transaction]:
        """Extract transaction data from text and tables"""
        
        transactions = []
        
        # Try to extract from tables first
        if tables:
            transactions.extend(self._extract_from_tables(tables))
        
        # Extract from text using regex patterns
        transactions.extend(self._extract_from_text(text))
        
        return transactions
    
    def _extract_from_tables(self, tables: List[List[List[str]]]) -> List[Transaction]:
        """Extract transactions from table data"""
        
        transactions = []
        
        for table in tables:
            if len(table) < 2:  # Need at least header and one row
                continue
            
            # Look for transaction-like tables
            header = table[0] if table[0] else []
            if not any(col and ('date' in col.lower() or 'amount' in col.lower() or 'description' in col.lower()) for col in header):
                continue
            
            # Find column indices
            date_col = next((i for i, col in enumerate(header) if col and 'date' in col.lower()), None)
            desc_col = next((i for i, col in enumerate(header) if col and ('description' in col.lower() or 'particulars' in col.lower())), None)
            amount_col = next((i for i, col in enumerate(header) if col and 'amount' in col.lower()), None)
            balance_col = next((i for i, col in enumerate(header) if col and 'balance' in col.lower()), None)
            
            # Extract transactions
            for row in table[1:]:
                if len(row) <= max(filter(None, [date_col, desc_col, amount_col, balance_col])):
                    continue
                
                try:
                    transaction = Transaction(
                        date=row[date_col] if date_col is not None and len(row) > date_col else "",
                        description=row[desc_col] if desc_col is not None and len(row) > desc_col else "",
                        amount=self._parse_amount(row[amount_col] if amount_col is not None and len(row) > amount_col else "0"),
                        balance=self._parse_amount(row[balance_col] if balance_col is not None and len(row) > balance_col else None)
                    )
                    transactions.append(transaction)
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse table row: {e}")
                    continue
        
        return transactions
    
    def _extract_from_text(self, text: str) -> List[Transaction]:
        """Extract transactions from raw text using regex patterns"""
        
        transactions = []
        
        # Common transaction patterns
        patterns = [
            # DD/MM/YYYY Amount Description
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+([+-]?\d+[\d,]*\.?\d*)\s+(.+?)(?=\n|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|$)',
            # DD-MMM-YYYY Amount Description  
            r'(\d{1,2}-[A-Za-z]{3}-\d{2,4})\s+([+-]?\d+[\d,]*\.?\d*)\s+(.+?)(?=\n|\d{1,2}-[A-Za-z]{3}-\d{2,4}|$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            
            for match in matches:
                try:
                    date_str = match.group(1)
                    amount_str = match.group(2)
                    description = match.group(3).strip()
                    
                    transaction = Transaction(
                        date=date_str,
                        description=description,
                        amount=self._parse_amount(amount_str)
                    )
                    transactions.append(transaction)
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse text transaction: {e}")
                    continue
        
        return transactions
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        
        if not amount_str:
            return 0.0
        
        # Remove common currency symbols and formatting
        cleaned = re.sub(r'[₹$,\s]', '', str(amount_str))
        
        # Handle negative amounts in parentheses
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
