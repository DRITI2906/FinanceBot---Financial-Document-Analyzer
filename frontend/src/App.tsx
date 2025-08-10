import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import sessionManager from './sessionManager';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';

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

interface Thread {
  id: number;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [error, setError] = useState<string>('');
  const [expandedInsights, setExpandedInsights] = useState<Set<string>>(new Set());
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showSidebar, setShowSidebar] = useState(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const incoming = Array.from(e.target.files);
      setFiles((prev) => {
        const byKey = new Map<string, File>();
        prev.forEach((f) => byKey.set(`${f.name}|${f.size}|${f.lastModified}`, f));
        incoming.forEach((f) => byKey.set(`${f.name}|${f.size}|${f.lastModified}`, f));
        const merged = Array.from(byKey.values());
        try {
          const dt = new DataTransfer();
          merged.forEach((f) => dt.items.add(f));
          if (fileInputRef.current) fileInputRef.current.files = dt.files;
        } catch (_) {
          if (fileInputRef.current) fileInputRef.current.value = '';
        }
        return merged;
      });
      setError('');
    }
  };

  const removeFileAt = (index: number) => {
    setFiles((prev) => {
      const updated = prev.filter((_, i) => i !== index);
      try {
        const dt = new DataTransfer();
        updated.forEach((f) => dt.items.add(f));
        if (fileInputRef.current) fileInputRef.current.files = dt.files;
      } catch (_) {
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
      return updated;
    });
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
          ...sessionManager.getMultipartHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      });
      
      const list = response.data.results || [];
      const first = list[0] || null;
      setResults(list);
      setResult(first);
    } catch (error: any) {
      console.error('Upload error:', error);
      setError(error.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score <= 3) return '#10b981';
    if (score <= 6) return '#f59e0b';
    return '#ef4444';
  };

  const renderMarkdownLite = (text: string) => {
    return {
      __html: text
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>')
    };
  };

  const toggleInsight = (insightId: string) => {
    setExpandedInsights(prev => {
      const newSet = new Set(prev);
      if (newSet.has(insightId)) {
        newSet.delete(insightId);
      } else {
        newSet.add(insightId);
      }
      return newSet;
    });
  };

  const truncateText = (text: string, maxLength: number = 150) => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  const loadThreads = async () => {
    try {
      const response = await axios.get('http://localhost:8000/threads', {
        headers: sessionManager.getHeaders()
      });
      setThreads(response.data.threads || []);
    } catch (error) {
      console.error('Error loading threads:', error);
    }
  };

  const loadThreadMessages = async (threadId: string) => {
    try {
      const response = await axios.get(`http://localhost:8000/threads/${threadId}/messages`, {
        headers: sessionManager.getHeaders()
      });
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Error loading thread messages:', error);
    }
  };

  const handleThreadSelect = (threadId: string) => {
    setCurrentThreadId(threadId);
    loadThreadMessages(threadId);
  };

  const handleNewThread = (threadId: string) => {
    setCurrentThreadId(threadId);
    setMessages([]);
  };

  const handleMessageSent = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  const handleNewMessage = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  useEffect(() => {
    loadThreads();
  }, []);

  return (
    <div className="App">
      <div className="app-header">
        <button 
          onClick={() => setShowSidebar(!showSidebar)} 
          className="sidebar-toggle"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <h1>🤖 FinanceBot</h1>
      </div>

      <div className="app-container">
        {showSidebar && (
          <Sidebar
            threads={threads}
            currentThreadId={currentThreadId}
            onThreadSelect={handleThreadSelect}
            onNewThread={handleNewThread}
            onThreadsUpdate={loadThreads}
          />
        )}

        <div className="main-content">
        <div className="upload-section">
            <div className="tip">
              💡 Upload your financial documents (PDF, DOCX, CSV, XLSX) to get AI-powered insights
            </div>
            
            <div className="file-list">
              {files.map((file, index) => (
                <div key={`${file.name}|${file.size}|${file.lastModified}`} className="file-item">
                  <span className="file-name">{file.name}</span>
                  <button
                    onClick={() => removeFileAt(index)}
                    className="clear-file-btn"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <div className="upload-controls">
            <input
                ref={fileInputRef}
              type="file"
                multiple
                accept=".pdf,.docx,.csv,.xlsx"
              onChange={handleFileChange}
              className="file-input"
            />
            <button
              onClick={handleUpload}
                disabled={loading || !files.length}
              className="upload-btn"
            >
                {loading ? '📊 Analyzing...' : '📊 Analyze'}
            </button>
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
                  {(results.length > 0 ? results : (result ? [result] : [])).flatMap((r) => r.summary.key_insights.map((insight, i) => {
                    const insightId = `${r.document_id}-${i}`;
                    const isExpanded = expandedInsights.has(insightId);
                    const displayText = isExpanded ? insight : truncateText(insight);
                    const shouldShowToggle = insight.length > 150;
                    
                    return (
                      <li key={insightId}>
                        <div dangerouslySetInnerHTML={renderMarkdownLite(displayText)}></div>
                        {shouldShowToggle && (
                <button
                            onClick={() => toggleInsight(insightId)}
                            className="read-more-btn"
                >
                            {isExpanded ? 'Read Less' : 'Read More'}
                </button>
                        )}
                      </li>
                    );
                  }))}
                </ul>
            </div>
          </div>
        )}

          <div className="chat-interface-container">
            <ChatInterface
              threadId={currentThreadId}
              messages={messages}
              onMessageSent={handleMessageSent}
              onNewMessage={handleNewMessage}
              documentIds={results.map(r => r.document_id)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;