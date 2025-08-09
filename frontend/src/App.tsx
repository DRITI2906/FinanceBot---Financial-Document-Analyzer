import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

interface AnalysisResult {
  document_id: string;
  filename: string;
  document_type: string;
  summary: {
    key_insights: string[];
  };
  risk_score: number;
  recommendations: string[];
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string>('');
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatAnswer, setChatAnswer] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!chatQuestion || !result) return;

    setChatLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/chat', {
        document_id: result.document_id,
        question: chatQuestion,
      });
      setChatAnswer(response.data.answer);
    } catch (err: any) {
      setChatAnswer('Chat failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setChatLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 7) return '#dc2626'; // red
    if (score >= 4) return '#ea580c'; // orange
    if (score >= 2) return '#ca8a04'; // yellow
    return '#16a34a'; // green
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🤖 FinanceBot</h1>
        <p>Powered by Google Gemini - Upload PDF documents for AI analysis</p>
      </header>

      <main className="main">
        <div className="upload-section">
          <h2>📄 Upload Financial Document</h2>
          <div className="upload-area">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="file-input"
            />
            {file && <p>Selected: {file.name}</p>}
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="upload-btn"
            >
              {loading ? '🔄 Analyzing...' : '📊 Analyze Document'}
            </button>
          </div>
          {error && <div className="error">{error}</div>}
        </div>

        {result && (
          <div className="results-section">
            <h2>📈 Analysis Results</h2>
            <div className="result-card">
              <h3>{result.filename}</h3>
              <div className="risk-score">
                <span>Risk Score: </span>
                <strong style={{ color: getRiskColor(result.risk_score) }}>
                  {result.risk_score.toFixed(1)}/10
                </strong>
              </div>
              <div className="document-type">
                <span>Type: </span>
                <strong>{result.document_type.replace('_', ' ')}</strong>
              </div>
            </div>

            <div className="insights">
              <h3>🔍 Key Insights</h3>
              <ul>
                {result.summary.key_insights.map((insight, index) => (
                  <li key={index}>{insight}</li>
                ))}
              </ul>
            </div>

            <div className="recommendations">
              <h3>💡 Recommendations</h3>
              <ul>
                {result.recommendations.map((rec, index) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            </div>

            <div className="chat-section">
              <h3>💬 Ask Questions About Your Document</h3>
              <div className="chat-input">
                <input
                  type="text"
                  placeholder="Ask something about your document..."
                  value={chatQuestion}
                  onChange={(e) => setChatQuestion(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleChat()}
                />
                <button
                  onClick={handleChat}
                  disabled={!chatQuestion || chatLoading}
                  className="chat-btn"
                >
                  {chatLoading ? '🤔' : '💬'}
                </button>
              </div>
              {chatAnswer && (
                <div className="chat-answer">
                  <strong>Answer:</strong>
                  <p>{chatAnswer}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;