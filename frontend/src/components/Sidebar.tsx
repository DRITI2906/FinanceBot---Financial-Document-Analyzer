import React from 'react';
import axios from 'axios';
import sessionManager from '../sessionManager';

interface Thread {
  id: number;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface SidebarProps {
  threads: Thread[];
  currentThreadId: string | null;
  onThreadSelect: (threadId: string) => void;
  onNewThread: (threadId: string) => void;
  onThreadsUpdate: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  threads,
  currentThreadId,
  onThreadSelect,
  onNewThread,
  onThreadsUpdate
}) => {
  const handleNewChat = async () => {
    try {
      const response = await axios.post(
        'http://localhost:8000/threads',
        {},
        {
          headers: sessionManager.getHeaders()
        }
      );
      
      const newThreadId = response.data.thread_id;
      onNewThread(newThreadId);
      onThreadsUpdate();
    } catch (error) {
      console.error('Error creating new thread:', error);
    }
  };

  const handleDeleteThread = async (threadId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return;
    }

    try {
      await axios.delete(
        `http://localhost:8000/threads/${threadId}`,
        {
          headers: sessionManager.getHeaders()
        }
      );
      onThreadsUpdate();
    } catch (error) {
      console.error('Error deleting thread:', error);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 168) { // 7 days
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <button onClick={handleNewChat} className="new-chat-button">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          New Chat
        </button>
      </div>
      
      <div className="threads-list">
        {threads.length === 0 ? (
          <div className="no-threads">
            <p>No conversations yet</p>
            <p>Start a new chat to begin!</p>
          </div>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.thread_id}
              className={`thread-item ${currentThreadId === thread.thread_id ? 'active' : ''}`}
              onClick={() => onThreadSelect(thread.thread_id)}
            >
              <div className="thread-content">
                <div className="thread-title">{thread.title}</div>
                <div className="thread-meta">
                  <span className="message-count">{thread.message_count} messages</span>
                  <span className="thread-date">{formatDate(thread.updated_at)}</span>
                </div>
              </div>
              <button
                onClick={(e) => handleDeleteThread(thread.thread_id, e)}
                className="delete-thread-button"
                title="Delete conversation"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3,6 5,6 21,6"></polyline>
                  <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Sidebar;
