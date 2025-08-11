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

type ThreadViewMode = 'upload' | 'chat';

interface ThreadUploadState {
  files: File[];
  loading: boolean;
  error: string;
  results: AnalysisResult[];
  result: AnalysisResult | null;
}

function App() {
  // Per-thread upload state and view mode
  const [threadUploads, setThreadUploads] = useState<Record<string, ThreadUploadState>>({});
  const [threadView, setThreadView] = useState<Record<string, ThreadViewMode>>({});
  const [expandedInsights, setExpandedInsights] = useState<Set<string>>(new Set());
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showSidebar, setShowSidebar] = useState(true);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const getDefaultUploadState = (): ThreadUploadState => ({
    files: [],
    loading: false,
    error: '',
    results: [],
    result: null,
  });

  const getCurrentUploadState = (): ThreadUploadState => {
    if (!currentThreadId) return getDefaultUploadState();
    return threadUploads[currentThreadId] || getDefaultUploadState();
  };

  const setCurrentUploadState = (updater: (prev: ThreadUploadState) => ThreadUploadState) => {
    if (!currentThreadId) return;
    setThreadUploads(prev => ({
      ...prev,
      [currentThreadId]: updater(prev[currentThreadId] || getDefaultUploadState()),
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!currentThreadId) {
      // No thread selected; ignore file changes
      return;
    }
    if (e.target.files && e.target.files.length > 0) {
      const incoming = Array.from(e.target.files);
      setCurrentUploadState((prev) => {
        const byKey = new Map<string, File>();
        prev.files.forEach((f) => byKey.set(`${f.name}|${f.size}|${f.lastModified}`, f));
        incoming.forEach((f) => byKey.set(`${f.name}|${f.size}|${f.lastModified}`, f));
        const merged = Array.from(byKey.values());
        try {
          const dt = new DataTransfer();
          merged.forEach((f) => dt.items.add(f));
          if (fileInputRef.current) fileInputRef.current.files = dt.files;
        } catch (_) {
          if (fileInputRef.current) fileInputRef.current.value = '';
        }
        return { ...prev, files: merged, error: '' };
      });
    }
  };

  const removeFileAt = (index: number) => {
    if (!currentThreadId) return;
    setCurrentUploadState((prev) => {
      const updated = prev.files.filter((_, i) => i !== index);
      try {
        const dt = new DataTransfer();
        updated.forEach((f) => dt.items.add(f));
        if (fileInputRef.current) fileInputRef.current.files = dt.files;
      } catch (_) {
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
      return { ...prev, files: updated };
    });
  };

  const handleUpload = async () => {
    if (!currentThreadId) return;
    const { files } = getCurrentUploadState();
    if (!files.length) {
      setCurrentUploadState((prev) => ({ ...prev, error: 'Please select a file (.pdf, .docx, .csv, .xlsx)' }));
      return;
    }

    setCurrentUploadState((prev) => ({ ...prev, loading: true, error: '' }));

    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    // Attach thread id so backend can associate documents with the thread
    formData.append('thread_id', currentThreadId);

    try {
      const response = await axios.post('http://localhost:8000/upload-multiple', formData, {
        headers: {
          ...sessionManager.getMultipartHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      });
      const list = response.data.results || [];
      const first = list[0] || null;
      // Merge with any existing results for this thread
      setCurrentUploadState((prev) => {
        const existingById = new Map<string, AnalysisResult>();
        prev.results.forEach((r) => existingById.set(r.document_id, r));
        list.forEach((r: AnalysisResult) => existingById.set(r.document_id, r));
        const merged = Array.from(existingById.values());
        return { ...prev, results: merged, result: first };
      });
      // Refresh threads to pull possible new title from backend
      loadThreads();
    } catch (error: any) {
      console.error('Upload error:', error);
      setCurrentUploadState((prev) => ({ ...prev, error: error.response?.data?.detail || 'Upload failed' }));
    } finally {
      setCurrentUploadState((prev) => ({ ...prev, loading: false }));
    }
  };

  const loadThreadDocuments = async (threadId: string) => {
    try {
      const response = await axios.get(`http://localhost:8000/threads/${threadId}/documents`, {
        headers: sessionManager.getHeaders(),
      });
      const docs = response.data.documents || [];
      const mapped: AnalysisResult[] = docs.map((d: any) => {
        const summaryObj = d.summary || {};
        const innerSummary = summaryObj.summary || {};
        return {
          document_id: d.document_id,
          filename: d.filename,
          document_type: summaryObj.document_type || d.document_type || 'unknown',
          summary: {
            key_insights: innerSummary.key_insights || [],
          },
          risk_score: summaryObj.risk_score ?? d.risk_score ?? 0,
          recommendations: summaryObj.recommendations || [],
        } as AnalysisResult;
      });
      setThreadUploads((prev) => ({
        ...prev,
        [threadId]: {
          ...(prev[threadId] || getDefaultUploadState()),
          results: mapped,
          result: mapped[0] || null,
        },
      }));
    } catch (error) {
      console.error('Error loading thread documents:', error);
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
    // Ensure upload state exists for the selected thread
    setThreadUploads(prev => ({
      ...prev,
      [threadId]: prev[threadId] || getDefaultUploadState(),
    }));
    // Always show upload first when opening a chat
    setThreadView(prev => ({ ...prev, [threadId]: 'upload' }));
    loadThreadMessages(threadId);
    loadThreadDocuments(threadId);
  };

  const handleNewThread = (threadId: string) => {
    setCurrentThreadId(threadId);
    setMessages([]);
    setThreadUploads(prev => ({ ...prev, [threadId]: getDefaultUploadState() }));
    setThreadView(prev => ({ ...prev, [threadId]: 'upload' }));
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

  const currentUploads = getCurrentUploadState();
  const currentMode: ThreadViewMode = currentThreadId ? (threadView[currentThreadId] || 'upload') : 'upload';

  // Keep the file input's FileList in sync with the current thread's files
  useEffect(() => {
    if (!fileInputRef.current) return;
    try {
      const dt = new DataTransfer();
      currentUploads.files.forEach((f) => dt.items.add(f));
      fileInputRef.current.files = dt.files;
    } catch (_) {
      try {
        if (fileInputRef.current) fileInputRef.current.value = '';
      } catch {}
    }
  }, [currentThreadId, currentUploads.files]);

  return (
    <div className="App">
      <div className="app-header">
        <div className="app-header-inner">
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
          {/* Upload View */}
          {currentThreadId && currentMode === 'upload' && (
            <>
              <div className="upload-section">
                <div className="tip">
                  💡 Upload your financial documents (PDF, DOCX, CSV, XLSX) to get AI-powered insights
                </div>

                <div className="file-list">
                  {currentUploads.files.map((file, index) => (
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
                    disabled={!currentThreadId}
                  />
                  <button
                    onClick={handleUpload}
                    disabled={currentUploads.loading || !currentUploads.files.length}
                    className="upload-btn"
                  >
                    {currentUploads.loading ? '📊 Analyzing...' : '📊 Analyze'}
                  </button>
                  <button
                    onClick={() => currentThreadId && setThreadView(prev => ({ ...prev, [currentThreadId]: 'chat' }))}
                    className="upload-btn"
                  >
                    💬 Chat with Bot
                  </button>
                </div>
                {currentUploads.error && <div className="error">{currentUploads.error}</div>}
              </div>

              {(currentUploads.results.length > 0 || currentUploads.result) && (
                <div className="results-section">
                  <h2>📈 Analysis Results</h2>
                  {(currentUploads.results.length > 0 ? currentUploads.results : (currentUploads.result ? [currentUploads.result] : [])).map((r) => (
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
                      {(currentUploads.results.length > 0 ? currentUploads.results : (currentUploads.result ? [currentUploads.result] : [])).flatMap((r) => r.summary.key_insights.map((insight, i) => {
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
            </>
          )}

          {/* Chat View */}
          {currentThreadId && currentMode === 'chat' && (
            <div className="chat-interface-container">
              <div style={{ marginBottom: 8 }}>
                <button
                  className="upload-btn"
                  onClick={() => currentThreadId && setThreadView(prev => ({ ...prev, [currentThreadId]: 'upload' }))}
                >
                  ⬅️ Back to Upload
                </button>
              </div>
              <ChatInterface
                threadId={currentThreadId}
                messages={messages}
                onMessageSent={handleMessageSent}
                onNewMessage={handleNewMessage}
                documentIds={currentUploads.results.map(r => r.document_id)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;