from typing import List
import statistics

from .models import Transaction, Anomaly, RiskLevel, DocumentType

class RiskAnalyzer:
    """
    Calculates overall risk scores based on transactions and anomalies
    """
    
    def __init__(self):
        pass
    
    async def calculate_risk_score(
        self,
        transactions: List[Transaction],
        anomalies: List[Anomaly],
        document_type: DocumentType
    ) -> float:
        """
        Calculate overall risk score (0-10 scale)
        """
        
        if not transactions and not anomalies:
            return 0.0
        
        # Base risk from anomalies
        anomaly_risk = self._calculate_anomaly_risk(anomalies)
        
        # Transaction pattern risk
        transaction_risk = self._calculate_transaction_risk(transactions)
        
        # Document type risk modifier
        doc_type_modifier = self._get_document_type_modifier(document_type)
        
        # Combine scores
        base_score = (anomaly_risk * 0.6) + (transaction_risk * 0.4)
        final_score = base_score * doc_type_modifier
        
        # Ensure score is between 0 and 10
        return min(10.0, max(0.0, final_score))
    
    def _calculate_anomaly_risk(self, anomalies: List[Anomaly]) -> float:
        """Calculate risk score based on anomalies"""
        
        if not anomalies:
            return 0.0
        
        # Risk weights for different anomaly types
        risk_weights = {
            "high_value_transaction": 3.0,
            "high_risk_merchants": 4.0,
            "foreign_transactions": 2.0,
            "overdraft_detected": 4.5,
            "negative_balance": 4.0,
            "suspicious_keywords": 2.5,
            "potential_duplicate": 1.5,
            "unusual_timing": 1.0,
            "high_frequency_similar_transactions": 2.0,
            "statistical_outlier": 1.5,
            "excessive_round_numbers": 0.5,
            "overdue_payment": 2.0
        }
        
        # Risk level multipliers
        risk_level_multipliers = {
            RiskLevel.LOW: 0.5,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 2.0,
            RiskLevel.CRITICAL: 3.0
        }
        
        total_risk = 0.0
        for anomaly in anomalies:
            base_weight = risk_weights.get(anomaly.type, 1.0)
            level_multiplier = risk_level_multipliers.get(anomaly.risk_level, 1.0)
            confidence_factor = anomaly.confidence
            
            anomaly_score = base_weight * level_multiplier * confidence_factor
            total_risk += anomaly_score
        
        # Normalize based on number of anomalies
        if len(anomalies) > 0:
            average_risk = total_risk / len(anomalies)
            # Apply diminishing returns for multiple anomalies
            return min(8.0, average_risk + (len(anomalies) * 0.1))
        
        return 0.0
    
    def _calculate_transaction_risk(self, transactions: List[Transaction]) -> float:
        """Calculate risk score based on transaction patterns"""
        
        if not transactions:
            return 0.0
        
        risk_factors = []
        
        # Volume risk - very high number of transactions
        if len(transactions) > 100:
            risk_factors.append(1.0)
        elif len(transactions) > 50:
            risk_factors.append(0.5)
        
        # Amount variance risk
        amounts = [abs(t.amount) for t in transactions if t.amount != 0]
        if len(amounts) > 1:
            mean_amount = statistics.mean(amounts)
            std_amount = statistics.stdev(amounts)
            
            # High variance might indicate irregular patterns
            if std_amount > mean_amount * 2:  # Very high variance
                risk_factors.append(1.5)
            elif std_amount > mean_amount:  # High variance
                risk_factors.append(0.8)
        
        # Large transaction risk
        if amounts:
            max_amount = max(amounts)
            if max_amount > 1000000:  # > 10L
                risk_factors.append(2.0)
            elif max_amount > 500000:  # > 5L
                risk_factors.append(1.0)
            elif max_amount > 100000:  # > 1L
                risk_factors.append(0.5)
        
        # Negative transaction patterns (more debits than credits for bank statements)
        debits = [t for t in transactions if t.amount < 0]
        credits = [t for t in transactions if t.amount > 0]
        
        if len(debits) > len(credits) * 3:  # Much more debits than credits
            risk_factors.append(1.0)
        
        # Calculate average risk
        if risk_factors:
            return min(5.0, sum(risk_factors) / len(risk_factors))
        
        return 0.0
    
    def _get_document_type_modifier(self, document_type: DocumentType) -> float:
        """Get risk modifier based on document type"""
        
        modifiers = {
            DocumentType.BANK_STATEMENT: 1.0,  # Standard baseline
            DocumentType.INVOICE: 0.8,  # Generally lower risk
            DocumentType.ANNUAL_REPORT: 0.6,  # Usually reviewed documents
            DocumentType.TRANSACTION_HISTORY: 1.2,  # Might have more irregular patterns
            DocumentType.OTHER: 0.9  # Unknown type, slightly reduced confidence
        }
        
        return modifiers.get(document_type, 1.0)
