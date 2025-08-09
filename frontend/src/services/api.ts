import axios from 'axios';
import { AnalysisResult, ProcessedDocument } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Upload and analyze document
  uploadDocument: async (file: File): Promise<AnalysisResult> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },

  // Chat with document
  chatWithDocument: async (documentId: string, question: string): Promise<{ answer: string; document_id: string }> => {
    const response = await api.post('/chat', {
      document_id: documentId,
      question,
    });
    
    return response.data;
  },

  // Get list of documents
  getDocuments: async (): Promise<{ documents: ProcessedDocument[] }> => {
    const response = await api.get('/documents');
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; message: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
