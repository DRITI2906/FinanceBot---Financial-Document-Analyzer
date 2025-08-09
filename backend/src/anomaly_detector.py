from typing import List, Dict, Any
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

from .models import Transaction, Anomaly, RiskLevel, DocumentType
from .config import get_settings

class AnomalyDetector:
    """
    Detects various types of anomalies in financial transactions
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def detect_anomalies(
        self, 
        transactions: List[Transaction], 
        document_type: DocumentType,
        raw_text: str
    ) -> List[Anomaly]:
        """
        Main anomaly detection function
        """
        
        anomalies = []
        
        if not transactions:
            return anomalies
        
        # Different detection methods
        anomalies.extend(self._detect_amount_anomalies(transactions))
        anomalies.extend(self._detect_frequency_anomalies(transactions))
        anomalies.extend(self._detect_duplicate_transactions(transactions))
        anomalies.extend(self._detect_round_number_anomalies(transactions))
        anomalies.extend(self._detect_time_pattern_anomalies(transactions))
        anomalies.extend(self._detect_description_anomalies(transactions))
        anomalies.extend(self._detect_foreign_transactions(transactions, raw_text))
        anomalies.extend(self._detect_high_risk_merchants(transactions))
        
        # Document-specific anomalies
        if document_type == DocumentType.BANK_STATEMENT:
            anomalies.extend(self._detect_bank_statement_anomalies(transactions, raw_text))
        elif document_type == DocumentType.INVOICE:
            anomalies.extend(self._detect_invoice_anomalies(transactions, raw_text))
        
        return anomalies
    
    def _detect_amount_anomalies(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect transactions with unusual amounts"""
        
        anomalies = []
        amounts = [abs(t.amount) for t in transactions if t.amount != 0]
        
        if len(amounts) < 3:
            return anomalies
        
        # Calculate statistical thresholds
        mean_amount = statistics.mean(amounts)
        std_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0
        high_threshold = mean_amount + (3 * std_amount)
        
        # Very high amount threshold from settings
        very_high_threshold = self.settings.high_risk_transaction_amount
        
        for transaction in transactions:
            amount = abs(transaction.amount)
            
            # Extremely high amounts
            if amount > very_high_threshold:
                anomalies.append(Anomaly(
                    type="high_value_transaction",
                    description=f"Very high transaction amount: ₹{amount:,.2f}",
                    risk_level=RiskLevel.HIGH,
                    confidence=0.9,
                    details={
                        "amount": amount,
                        "threshold": very_high_threshold,
                        "transaction": transaction.dict()
                    }
                ))
            
            # Statistical outliers
            elif amount > high_threshold and std_amount > 0:
                anomalies.append(Anomaly(
                    type="statistical_outlier",
                    description=f"Amount significantly higher than average: ₹{amount:,.2f} (avg: ₹{mean_amount:,.2f})",
                    risk_level=RiskLevel.MEDIUM,
                    confidence=0.7,
                    details={
                        "amount": amount,
                        "mean": mean_amount,
                        "std_dev": std_amount,
                        "transaction": transaction.dict()
                    }
                ))
        
        return anomalies
    
    def _detect_frequency_anomalies(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect unusual transaction frequency patterns"""
        
        anomalies = []
        
        # Group by description similarity
        similar_groups = defaultdict(list)
        for transaction in transactions:
            # Simplified grouping by first few words
            key = ' '.join(transaction.description.split()[:3]).lower()
            similar_groups[key].append(transaction)
        
        # Check for high frequency patterns
        for description, group_transactions in similar_groups.items():
            if len(group_transactions) >= 5:  # 5 or more similar transactions
                
                # Check if amounts are also similar (potential fraud)
                amounts = [t.amount for t in group_transactions]
                if len(set(amounts)) <= 2:  # Only 1-2 unique amounts
                    anomalies.append(Anomaly(
                        type="high_frequency_similar_transactions",
                        description=f"Multiple similar transactions: {len(group_transactions)} transactions to '{description}'",
                        risk_level=RiskLevel.MEDIUM,
                        confidence=0.8,
                        details={
                            "count": len(group_transactions),
                            "description_pattern": description,
                            "amounts": amounts,
                            "transactions": [t.dict() for t in group_transactions]
                        }
                    ))
        
        return anomalies
    
    def _detect_duplicate_transactions(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect potential duplicate transactions"""
        
        anomalies = []
        
        # Group by amount and description
        transaction_groups = defaultdict(list)
        for transaction in transactions:
            key = (transaction.amount, transaction.description.strip().lower())
            transaction_groups[key].append(transaction)
        
        for (amount, description), group in transaction_groups.items():
            if len(group) > 1:
                # Check if dates are close (potential duplicates)
                dates = [t.date for t in group if t.date]
                if len(dates) >= 2:
                    # Simple date proximity check (same day or consecutive days)
                    date_set = set(dates)
                    if len(date_set) == 1 or any(
                        abs(self._parse_date_simple(d1) - self._parse_date_simple(d2)).days <= 1
                        for d1 in dates for d2 in dates if d1 != d2
                    ):
                        anomalies.append(Anomaly(
                            type="potential_duplicate",
                            description=f"Potential duplicate transactions: ₹{amount} - {description}",
                            risk_level=RiskLevel.MEDIUM,
                            confidence=0.7,
                            details={
                                "count": len(group),
                                "amount": amount,
                                "description": description,
                                "transactions": [t.dict() for t in group]
                            }
                        ))
        
        return anomalies
    
    def _detect_round_number_anomalies(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect suspicious round number patterns"""
        
        anomalies = []
        
        round_amounts = []
        for transaction in transactions:
            amount = abs(transaction.amount)
            # Check if amount is a round number (ends in 000, 500, etc.)
            if amount >= 1000 and (amount % 1000 == 0 or amount % 500 == 0):
                round_amounts.append(transaction)
        
        # If too many round numbers, it might be suspicious
        if len(round_amounts) > len(transactions) * 0.3:  # More than 30% round numbers
            anomalies.append(Anomaly(
                type="excessive_round_numbers",
                description=f"High proportion of round number transactions: {len(round_amounts)}/{len(transactions)}",
                risk_level=RiskLevel.LOW,
                confidence=0.5,
                details={
                    "round_transaction_count": len(round_amounts),
                    "total_transactions": len(transactions),
                    "percentage": (len(round_amounts) / len(transactions)) * 100,
                    "round_transactions": [t.dict() for t in round_amounts[:5]]
                }
            ))
        
        return anomalies
    
    def _detect_time_pattern_anomalies(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect unusual timing patterns"""
        
        anomalies = []
        
        # Extract hour information if available in description
        night_transactions = []
        for transaction in transactions:
            # Look for time indicators in description
            time_pattern = re.search(r'(\d{1,2}):(\d{2})', transaction.description)
            if time_pattern:
                hour = int(time_pattern.group(1))
                if hour >= 23 or hour <= 5:  # Late night/early morning
                    night_transactions.append(transaction)
        
        if len(night_transactions) > 3:
            anomalies.append(Anomaly(
                type="unusual_timing",
                description=f"Multiple late-night transactions detected: {len(night_transactions)} transactions",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.6,
                details={
                    "count": len(night_transactions),
                    "transactions": [t.dict() for t in night_transactions]
                }
            ))
        
        return anomalies
    
    def _detect_description_anomalies(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect suspicious patterns in transaction descriptions"""
        
        anomalies = []
        
        # Suspicious keywords
        suspicious_keywords = [
            'cash', 'crypto', 'bitcoin', 'gambling', 'casino', 'betting',
            'loan', 'advance', 'urgent', 'emergency', 'wire transfer'
        ]
        
        suspicious_transactions = []
        for transaction in transactions:
            description_lower = transaction.description.lower()
            for keyword in suspicious_keywords:
                if keyword in description_lower:
                    suspicious_transactions.append((transaction, keyword))
                    break
        
        if suspicious_transactions:
            anomalies.append(Anomaly(
                type="suspicious_keywords",
                description=f"Transactions with potentially risky keywords: {len(suspicious_transactions)} found",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.6,
                details={
                    "count": len(suspicious_transactions),
                    "keywords_found": list(set([kw for _, kw in suspicious_transactions])),
                    "transactions": [t.dict() for t, _ in suspicious_transactions]
                }
            ))
        
        return anomalies
    
    def _detect_foreign_transactions(self, transactions: List[Transaction], raw_text: str) -> List[Anomaly]:
        """Detect foreign or international transactions"""
        
        anomalies = []
        
        # Look for foreign currency indicators
        foreign_indicators = ['usd', 'eur', 'gbp', 'foreign', 'international', 'overseas']
        foreign_transactions = []
        
        for transaction in transactions:
            description_lower = transaction.description.lower()
            if any(indicator in description_lower for indicator in foreign_indicators):
                foreign_transactions.append(transaction)
        
        # Also check raw text for foreign transaction indicators
        raw_text_lower = raw_text.lower()
        has_foreign_indicators = any(indicator in raw_text_lower for indicator in foreign_indicators)
        
        if foreign_transactions or has_foreign_indicators:
            anomalies.append(Anomaly(
                type="foreign_transactions",
                description=f"Foreign/international transactions detected: {len(foreign_transactions)} transactions",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.7,
                details={
                    "count": len(foreign_transactions),
                    "transactions": [t.dict() for t in foreign_transactions],
                    "text_indicators": has_foreign_indicators
                }
            ))
        
        return anomalies
    
    def _detect_high_risk_merchants(self, transactions: List[Transaction]) -> List[Anomaly]:
        """Detect transactions with high-risk merchant categories"""
        
        anomalies = []
        
        # High-risk merchant patterns
        high_risk_patterns = [
            'atm', 'casino', 'gambling', 'betting', 'lottery',
            'pawn shop', 'check cashing', 'payday loan',
            'money transfer', 'western union', 'moneygram'
        ]
        
        risky_transactions = []
        for transaction in transactions:
            description_lower = transaction.description.lower()
            for pattern in high_risk_patterns:
                if pattern in description_lower:
                    risky_transactions.append((transaction, pattern))
                    break
        
        if risky_transactions:
            anomalies.append(Anomaly(
                type="high_risk_merchants",
                description=f"Transactions with high-risk merchants: {len(risky_transactions)} found",
                risk_level=RiskLevel.HIGH,
                confidence=0.8,
                details={
                    "count": len(risky_transactions),
                    "risk_patterns": list(set([pattern for _, pattern in risky_transactions])),
                    "transactions": [t.dict() for t, _ in risky_transactions]
                }
            ))
        
        return anomalies
    
    def _detect_bank_statement_anomalies(self, transactions: List[Transaction], raw_text: str) -> List[Anomaly]:
        """Bank statement specific anomaly detection"""
        
        anomalies = []
        
        # Check for overdraft indicators
        overdraft_keywords = ['overdraft', 'overdrawn', 'insufficient funds', 'nsf', 'returned check']
        if any(keyword in raw_text.lower() for keyword in overdraft_keywords):
            anomalies.append(Anomaly(
                type="overdraft_detected",
                description="Overdraft or insufficient funds indicators found",
                risk_level=RiskLevel.HIGH,
                confidence=0.9,
                details={"keywords_found": [kw for kw in overdraft_keywords if kw in raw_text.lower()]}
            ))
        
        # Check for negative balances in transactions
        negative_balance_transactions = [t for t in transactions if t.balance and t.balance < 0]
        if negative_balance_transactions:
            anomalies.append(Anomaly(
                type="negative_balance",
                description=f"Negative account balance detected in {len(negative_balance_transactions)} transactions",
                risk_level=RiskLevel.HIGH,
                confidence=0.9,
                details={
                    "count": len(negative_balance_transactions),
                    "min_balance": min(t.balance for t in negative_balance_transactions),
                    "transactions": [t.dict() for t in negative_balance_transactions[:3]]
                }
            ))
        
        return anomalies
    
    def _detect_invoice_anomalies(self, transactions: List[Transaction], raw_text: str) -> List[Anomaly]:
        """Invoice specific anomaly detection"""
        
        anomalies = []
        
        # Check for overdue indicators
        overdue_keywords = ['overdue', 'past due', 'late payment', 'penalty', 'interest charges']
        if any(keyword in raw_text.lower() for keyword in overdue_keywords):
            anomalies.append(Anomaly(
                type="overdue_payment",
                description="Overdue payment indicators found",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.8,
                details={"keywords_found": [kw for kw in overdue_keywords if kw in raw_text.lower()]}
            ))
        
        return anomalies
    
    def _parse_date_simple(self, date_str: str) -> datetime:
        """Simple date parsing for comparison"""
        
        try:
            # Try common formats
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If all fail, return a default date
            return datetime.now()
        
        except:
            return datetime.now()
