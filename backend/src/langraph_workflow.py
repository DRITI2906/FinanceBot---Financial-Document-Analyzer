from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from typing import Dict, List, Any, TypedDict
import uuid
import json
from datetime import datetime
import asyncio
import logging

from .document_processor import DocumentProcessor
from .anomaly_detector import AnomalyDetector
from .risk_analyzer import RiskAnalyzer
from .models import AnalysisResult, Transaction, Summary, DocumentType, Anomaly, RiskLevel
from .config import get_settings

class WorkflowState(TypedDict):
    document_id: str
    filename: str
    file_path: str
    extracted_data: Dict[str, Any]
    document_type: DocumentType
    transactions: List[Transaction]
    summary: Summary
    anomalies: List[Anomaly]
    risk_score: float
    recommendations: List[str]
    chat_history: List[Dict[str, str]]

class FinancialAnalysisWorkflow:
    """
    LangGraph workflow for financial document analysis
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.default_llm,
            temperature=self.settings.temperature,
            api_key=self.settings.openai_api_key
        )
        self.document_processor = DocumentProcessor()
        self.anomaly_detector = AnomalyDetector()
        self.risk_analyzer = RiskAnalyzer()
        self.logger = logging.getLogger(__name__)
        
        # Store processed documents in memory (in production, use a database)
        self.processed_documents: Dict[str, WorkflowState] = {}
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("parse_document", self._parse_document)
        workflow.add_node("extract_transactions", self._extract_transactions)
        workflow.add_node("generate_summary", self._generate_summary)
        workflow.add_node("detect_anomalies", self._detect_anomalies)
        workflow.add_node("calculate_risk", self._calculate_risk)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        
        # Define the flow
        workflow.set_entry_point("parse_document")
        workflow.add_edge("parse_document", "extract_transactions")
        workflow.add_edge("extract_transactions", "generate_summary")
        workflow.add_edge("generate_summary", "detect_anomalies")
        workflow.add_edge("detect_anomalies", "calculate_risk")
        workflow.add_edge("calculate_risk", "generate_recommendations")
        workflow.add_edge("generate_recommendations", END)
        
        return workflow.compile()
    
    async def process_document(self, file_path: str, filename: str) -> AnalysisResult:
        """Process a document through the complete workflow"""
        
        document_id = str(uuid.uuid4())
        
        # Initialize state
        initial_state = WorkflowState(
            document_id=document_id,
            filename=filename,
            file_path=file_path,
            extracted_data={},
            document_type=DocumentType.OTHER,
            transactions=[],
            summary=Summary(
                total_transactions=0,
                total_amount=0.0,
                date_range={},
                top_categories=[],
                account_balances=[],
                key_insights=[]
            ),
            anomalies=[],
            risk_score=0.0,
            recommendations=[],
            chat_history=[]
        )
        
        # Run the workflow
        final_state = await self.workflow.ainvoke(initial_state)
        
        # Store the processed document
        self.processed_documents[document_id] = final_state
        
        # Create the analysis result
        result = AnalysisResult(
            document_id=document_id,
            filename=filename,
            document_type=final_state["document_type"],
            processed_at=datetime.now(),
            summary=final_state["summary"],
            transactions=final_state["transactions"],
            anomalies=final_state["anomalies"],
            risk_score=final_state["risk_score"],
            recommendations=final_state["recommendations"],
            extractable_data=final_state["extracted_data"]
        )
        
        return result
    
    async def _parse_document(self, state: WorkflowState) -> WorkflowState:
        """Parse the document and extract raw data"""
        
        self.logger.info(f"Parsing document: {state['filename']}")
        
        try:
            extracted_data = await self.document_processor.process_document(
                state["file_path"], 
                state["filename"]
            )
            
            state["extracted_data"] = extracted_data
            state["document_type"] = extracted_data["document_type"]
            
            return state
        
        except Exception as e:
            self.logger.error(f"Document parsing failed: {e}")
            raise
    
    async def _extract_transactions(self, state: WorkflowState) -> WorkflowState:
        """Extract structured transaction data"""
        
        self.logger.info("Extracting transactions")
        
        try:
            transactions = self.document_processor.extract_transactions(
                state["extracted_data"]["text"],
                state["extracted_data"]["tables"]
            )
            
            # Use LLM to enhance transaction extraction if needed
            if not transactions and state["extracted_data"]["text"]:
                transactions = await self._llm_extract_transactions(state["extracted_data"]["text"])
            
            state["transactions"] = transactions
            
            return state
        
        except Exception as e:
            self.logger.error(f"Transaction extraction failed: {e}")
            state["transactions"] = []
            return state
    
    async def _generate_summary(self, state: WorkflowState) -> WorkflowState:
        """Generate document summary using LLM"""
        
        self.logger.info("Generating summary")
        
        try:
            # Prepare context for LLM
            context = {
                "document_type": state["document_type"],
                "text_preview": state["extracted_data"]["text"][:2000],
                "transaction_count": len(state["transactions"]),
                "transactions_sample": state["transactions"][:5] if state["transactions"] else []
            }
            
            prompt = f"""
            Analyze this financial document and provide a comprehensive summary:
            
            Document Type: {context['document_type']}
            Transaction Count: {context['transaction_count']}
            
            Text Preview:
            {context['text_preview']}
            
            Sample Transactions:
            {json.dumps([t.dict() for t in context['transactions_sample']], indent=2)}
            
            Provide a JSON response with:
            1. total_amount: sum of all transaction amounts
            2. date_range: start and end dates
            3. top_categories: top spending categories
            4. account_balances: if available
            5. key_insights: important observations (3-5 points)
            """
            
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a financial analyst. Provide accurate, structured analysis of financial documents."),
                HumanMessage(content=prompt)
            ])
            
            # Parse LLM response
            summary_data = self._parse_summary_response(response.content, state["transactions"])
            state["summary"] = Summary(**summary_data)
            
            return state
        
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            # Fallback to basic summary
            state["summary"] = self._generate_basic_summary(state["transactions"])
            return state
    
    async def _detect_anomalies(self, state: WorkflowState) -> WorkflowState:
        """Detect anomalies and potential fraud"""
        
        self.logger.info("Detecting anomalies")
        
        try:
            anomalies = await self.anomaly_detector.detect_anomalies(
                state["transactions"],
                state["document_type"],
                state["extracted_data"]["text"]
            )
            
            state["anomalies"] = anomalies
            
            return state
        
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            state["anomalies"] = []
            return state
    
    async def _calculate_risk(self, state: WorkflowState) -> WorkflowState:
        """Calculate overall risk score"""
        
        self.logger.info("Calculating risk score")
        
        try:
            risk_score = await self.risk_analyzer.calculate_risk_score(
                state["transactions"],
                state["anomalies"],
                state["document_type"]
            )
            
            state["risk_score"] = risk_score
            
            return state
        
        except Exception as e:
            self.logger.error(f"Risk calculation failed: {e}")
            state["risk_score"] = 0.0
            return state
    
    async def _generate_recommendations(self, state: WorkflowState) -> WorkflowState:
        """Generate actionable recommendations"""
        
        self.logger.info("Generating recommendations")
        
        try:
            # Prepare context for LLM
            context = {
                "document_type": state["document_type"],
                "risk_score": state["risk_score"],
                "anomaly_count": len(state["anomalies"]),
                "high_risk_anomalies": [a for a in state["anomalies"] if a.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]],
                "total_amount": state["summary"].total_amount,
                "transaction_count": state["summary"].total_transactions
            }
            
            prompt = f"""
            Based on the financial analysis, provide actionable recommendations:
            
            Document Type: {context['document_type']}
            Risk Score: {context['risk_score']}/10
            Total Amount: ₹{context['total_amount']:,.2f}
            Transactions: {context['transaction_count']}
            High-Risk Anomalies: {len(context['high_risk_anomalies'])}
            
            High-Risk Issues:
            {json.dumps([{'type': a.type, 'description': a.description} for a in context['high_risk_anomalies']], indent=2)}
            
            Provide 3-7 specific, actionable recommendations to improve financial health and security.
            Focus on fraud prevention, cost optimization, and financial planning.
            """
            
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a financial advisor providing practical recommendations."),
                HumanMessage(content=prompt)
            ])
            
            recommendations = self._parse_recommendations(response.content)
            state["recommendations"] = recommendations
            
            return state
        
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            state["recommendations"] = ["Review transactions for accuracy", "Monitor account for unusual activity"]
            return state
    
    async def _llm_extract_transactions(self, text: str) -> List[Transaction]:
        """Use LLM to extract transactions when rule-based extraction fails"""
        
        prompt = f"""
        Extract financial transactions from this text. Look for dates, amounts, and descriptions.
        
        Text:
        {text[:3000]}
        
        Return a JSON array of transactions with fields: date, description, amount.
        Only include clear, identifiable transactions. If no transactions found, return empty array.
        """
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a data extraction specialist. Extract only clear, verifiable transaction data."),
                HumanMessage(content=prompt)
            ])
            
            # Parse the response and convert to Transaction objects
            transactions_data = json.loads(response.content)
            transactions = [Transaction(**t) for t in transactions_data if isinstance(t, dict)]
            
            return transactions
        
        except Exception as e:
            self.logger.warning(f"LLM transaction extraction failed: {e}")
            return []
    
    def _parse_summary_response(self, response: str, transactions: List[Transaction]) -> Dict[str, Any]:
        """Parse LLM summary response into structured data"""
        
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                summary_data = json.loads(json_match.group())
            else:
                summary_data = {}
            
            # Fallback calculations if LLM data is missing
            if not summary_data.get("total_amount"):
                summary_data["total_amount"] = sum(t.amount for t in transactions)
            
            if not summary_data.get("total_transactions"):
                summary_data["total_transactions"] = len(transactions)
            
            # Ensure required fields exist
            required_fields = {
                "total_transactions": len(transactions),
                "total_amount": sum(t.amount for t in transactions),
                "date_range": {},
                "top_categories": [],
                "account_balances": [],
                "key_insights": []
            }
            
            for field, default in required_fields.items():
                if field not in summary_data:
                    summary_data[field] = default
            
            return summary_data
        
        except Exception as e:
            self.logger.warning(f"Failed to parse summary response: {e}")
            return self._generate_basic_summary(transactions).dict()
    
    def _generate_basic_summary(self, transactions: List[Transaction]) -> Summary:
        """Generate basic summary from transactions"""
        
        total_amount = sum(t.amount for t in transactions)
        
        # Extract date range
        dates = [t.date for t in transactions if t.date]
        date_range = {}
        if dates:
            date_range = {"start": min(dates), "end": max(dates)}
        
        return Summary(
            total_transactions=len(transactions),
            total_amount=total_amount,
            date_range=date_range,
            top_categories=[],
            account_balances=[],
            key_insights=[f"Total of {len(transactions)} transactions worth ₹{total_amount:,.2f}"]
        )
    
    def _parse_recommendations(self, response: str) -> List[str]:
        """Parse recommendations from LLM response"""
        
        try:
            # Extract numbered or bulleted list
            import re
            
            # Look for numbered list
            numbered_items = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|$)', response, re.MULTILINE | re.DOTALL)
            if numbered_items:
                return [item.strip() for item in numbered_items]
            
            # Look for bulleted list
            bulleted_items = re.findall(r'[•\-\*]\s*(.+?)(?=\n[•\-\*]|\n\n|$)', response, re.MULTILINE | re.DOTALL)
            if bulleted_items:
                return [item.strip() for item in bulleted_items]
            
            # Split by lines and filter
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            recommendations = [line for line in lines if len(line) > 20 and not line.startswith(('Based on', 'The analysis', 'In summary'))]
            
            return recommendations[:7]  # Limit to 7 recommendations
        
        except Exception as e:
            self.logger.warning(f"Failed to parse recommendations: {e}")
            return ["Review the analysis results carefully", "Monitor for unusual patterns"]
    
    async def chat_query(self, document_id: str, question: str) -> str:
        """Handle chat queries about processed documents"""
        
        if document_id not in self.processed_documents:
            raise ValueError("Document not found")
        
        state = self.processed_documents[document_id]
        
        # Prepare context
        context = {
            "filename": state["filename"],
            "document_type": state["document_type"],
            "summary": state["summary"].dict(),
            "transaction_count": len(state["transactions"]),
            "transactions_sample": [t.dict() for t in state["transactions"][:10]],
            "anomalies": [a.dict() for a in state["anomalies"]],
            "risk_score": state["risk_score"]
        }
        
        prompt = f"""
        Answer the user's question about their financial document:
        
        Document: {context['filename']} ({context['document_type']})
        
        Summary: {json.dumps(context['summary'], indent=2)}
        
        Anomalies: {json.dumps(context['anomalies'], indent=2)}
        
        Risk Score: {context['risk_score']}/10
        
        Sample Transactions: {json.dumps(context['transactions_sample'], indent=2)}
        
        User Question: {question}
        
        Provide a helpful, accurate answer based on the document analysis.
        Include specific numbers and examples when relevant.
        """
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a helpful financial assistant. Answer questions accurately based on the document analysis."),
                HumanMessage(content=prompt)
            ])
            
            # Store in chat history
            state["chat_history"].append({
                "question": question,
                "answer": response.content,
                "timestamp": datetime.now().isoformat()
            })
            
            return response.content
        
        except Exception as e:
            self.logger.error(f"Chat query failed: {e}")
            return "I apologize, but I encountered an error processing your question. Please try again."
    
    async def get_processed_documents(self) -> List[Dict[str, Any]]:
        """Get list of processed documents"""
        
        documents = []
        for doc_id, state in self.processed_documents.items():
            documents.append({
                "document_id": doc_id,
                "filename": state["filename"],
                "document_type": state["document_type"],
                "risk_score": state["risk_score"],
                "transaction_count": len(state["transactions"]),
                "anomaly_count": len(state["anomalies"])
            })
        
        return documents
