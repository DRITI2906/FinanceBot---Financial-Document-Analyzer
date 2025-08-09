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
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [error, setError] = useState<string>('');
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatAnswer, setChatAnswer] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const incoming = Array.from(e.target.files);
      setFiles((prev) => {
        const byKey = new Map<string, File>();
        prev.forEach((f) => byKey.set(`${f.name}|${f.size}|${f.lastModified}`, f));
        incoming.forEach((f) => byKey.set(`${f.name}|${f.size}|${f.lastModified}`, f));
        return Array.from(byKey.values());
      });
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!files.length) {
      setError('Please select a file (.pdf, .docx, .csv, .xlsx)');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const response = await axios.post('http://localhost:8000/upload-multiple', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      const list = response.data.results || [];
      const first = list[0] || null;
      setResults(list);
      setResult(first);
      if (response.data.combined) {
        setChatAnswer(
          `Combined insights:\n- ${response.data.combined.key_insights.join('\n- ')}\n\nOverall risk: ${response.data.combined.risk_score}/10\n\nRecommendations:\n- ${response.data.combined.recommendations.join('\n- ')}`
        );
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!chatQuestion || ((results.length === 0 && !result) && files.length === 0)) return;

    setChatLoading(true);
    try {
      let answer = '';
      if (results.length <= 1 && result) {
        const response = await axios.post('http://localhost:8000/chat', {
          document_id: result.document_id,
          question: chatQuestion,
        });
        answer = response.data.answer;
      } else {
        // Ask across currently analyzed results (multi)
        const ids = results.map((r) => r.document_id);
        // Fallback: if results empty, upload now then ask
        if (ids.length === 0 && files.length > 0) {
          const formData = new FormData();
          files.forEach((f) => formData.append('files', f));
          const uploadResp = await axios.post('http://localhost:8000/upload-multiple', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          const list = uploadResp.data.results || [];
          setResults(list);
          ids.push(...list.map((r: any) => r.document_id));
        }
        const chatResp = await axios.post('http://localhost:8000/chat-multi', {
          document_ids: ids,
          question: chatQuestion,
        });
        answer = chatResp.data.answer;
      }
      setChatAnswer(answer);
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

  const renderMarkdownLite = (text: string) => {
    const escapeHtml = (s: string) =>
      s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    const normalize = (s: string) => {
      const lines = (s || '').split(/\r?\n/).map((l) => l.trimEnd());
      const cleaned = lines
        .map((line) => {
          if (/^\s*([*\-•])\s*$/.test(line)) return '';
          return line.replace(/^\s*(?:\d+\.\s+|[*\-•]\s+)/, '');
        })
        .filter((l) => l.length > 0);
      return cleaned.join('\n');
    };

    // 1) strip leading bullet markers from model output
    const stripped = normalize(text || '');
    // 2) escape HTML
    const escaped = escapeHtml(stripped);
    // 3) strong and em
    const withBold = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    const withEm = withBold.replace(/(^|[^*])\*(?!\*)([^*]+)\*(?!\*)/g, '$1<em>$2</em>');
    // 4) line breaks
    const withBreaks = withEm.replace(/\n/g, '<br/>');
    return { __html: withBreaks };
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
              accept=".pdf,.docx,.csv,.xlsx"
              multiple
              onChange={handleFileChange}
              className="file-input"
            />
            <p style={{ fontSize: '12px', color: '#6b7280' }}>Tip: Hold Ctrl or Shift to select multiple files</p>
            {files.length > 0 && (
              <div>
                <p>Selected files:</p>
                <ul>
                  {files.map((f, idx) => (
                    <li key={idx}>{f.name}</li>
                  ))}
                </ul>
              </div>
            )}
            <button
              onClick={handleUpload}
              disabled={!files.length || loading}
              className="upload-btn"
            >
              {loading ? '🔄 Analyzing...' : '📊 Analyze Document'}
            </button>
            {files.length > 0 && (
              <button
                onClick={() => setFiles([])}
                disabled={loading}
                style={{ marginLeft: 8 }}
                className="upload-btn"
              >
                Clear
              </button>
            )}
          </div>
          {error && <div className="error">{error}</div>}
        </div>

        {(results.length > 0 || result) && (
          <div className="results-section">
            <h2>📈 Analysis Results</h2>
            {(results.length > 0 ? results : (result ? [result] : [])).map((r, idx) => (
              <div className="result-card" key={r.document_id}>
                <h3>{r.filename}</h3>
                <div className="risk-score">
                  <span>Risk Score: </span>
                  <strong style={{ color: getRiskColor(r.risk_score) }}>
                    {r.risk_score.toFixed(1)}/10
                  </strong>
                </div>
                <div className="document-type">
                  <span>Type: </span>
                  <strong>{r.document_type.replace('_', ' ')}</strong>
                </div>
              </div>
            ))}

            <div className="insights">
              <h3>🔍 Key Insights</h3>
              <ul>
                {(results.length > 0 ? results : (result ? [result] : [])).flatMap((r) => r.summary.key_insights.map((insight, i) => (
                  <li key={`${r.document_id}-${i}`} dangerouslySetInnerHTML={renderMarkdownLite(insight)}></li>
                )))}
              </ul>
            </div>

            <div className="recommendations">
              <h3>💡 Recommendations</h3>
              <ul>
                {(results.length > 0 ? results : (result ? [result] : [])).flatMap((r) => r.recommendations.map((rec, i) => (
                  <li key={`${r.document_id}-rec-${i}`} dangerouslySetInnerHTML={renderMarkdownLite(rec)}></li>
                )))}
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
                  <p dangerouslySetInnerHTML={renderMarkdownLite(chatAnswer)} />
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