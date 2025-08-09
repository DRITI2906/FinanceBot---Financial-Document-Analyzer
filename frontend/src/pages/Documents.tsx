import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ProcessedDocument } from '../types';
import { apiService } from '../services/api';
import RiskBadge from '../components/RiskBadge';
import { 
  DocumentTextIcon,
  FolderOpenIcon,
  MagnifyingGlassIcon,
  CalendarIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<ProcessedDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<string>('all');

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await apiService.getDocuments();
      setDocuments(response.documents || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevel = (score: number): 'low' | 'medium' | 'high' | 'critical' => {
    if (score >= 8) return 'critical';
    if (score >= 6) return 'high';
    if (score >= 3) return 'medium';
    return 'low';
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         doc.document_type.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filterRisk === 'all') return matchesSearch;
    
    const riskLevel = getRiskLevel(doc.risk_score);
    return matchesSearch && riskLevel === filterRisk;
  });

  const DocumentCard: React.FC<{ doc: ProcessedDocument; index: number }> = ({ doc, index }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-all duration-200 overflow-hidden"
    >
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <DocumentTextIcon className="w-8 h-8 text-gray-400" />
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">{doc.filename}</h3>
              <p className="text-sm text-gray-500 capitalize">
                {doc.document_type.replace('_', ' ')}
              </p>
            </div>
          </div>
          <RiskBadge riskLevel={getRiskLevel(doc.risk_score)} />
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <ChartBarIcon className="w-4 h-4" />
            <span>Risk: {doc.risk_score.toFixed(1)}/10</span>
          </div>
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <DocumentTextIcon className="w-4 h-4" />
            <span>{doc.transaction_count} transactions</span>
          </div>
        </div>

        {doc.anomaly_count > 0 && (
          <div className="mb-4 p-3 bg-warning-50 border border-warning-200 rounded-lg">
            <div className="flex items-center space-x-2 text-sm text-warning-800">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>{doc.anomaly_count} anomalies detected</span>
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <Link
            to={`/analysis/${doc.document_id}`}
            className="btn-primary"
          >
            View Analysis
          </Link>
        </div>
      </div>
    </motion.div>
  );

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="loading-spinner w-8 h-8 text-primary-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading documents...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Document Library</h1>
        <p className="mt-1 text-gray-600">
          View and manage all your analyzed financial documents
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0 sm:space-x-4">
          {/* Search */}
          <div className="relative flex-1 max-w-lg">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Risk Filter */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Filter by risk:</label>
            <select
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Levels</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
              <option value="critical">Critical Risk</option>
            </select>
          </div>
        </div>
      </div>

      {/* Documents Grid */}
      {filteredDocuments.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocuments.map((doc, index) => (
            <DocumentCard key={doc.document_id} doc={doc} index={index} />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12">
          <FolderOpenIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Documents Yet</h3>
          <p className="text-gray-600 mb-6">
            Upload your first financial document to get started with AI analysis.
          </p>
          <Link to="/" className="btn-primary">
            Upload Document
          </Link>
        </div>
      ) : (
        <div className="text-center py-12">
          <MagnifyingGlassIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Documents Found</h3>
          <p className="text-gray-600">
            Try adjusting your search terms or filters.
          </p>
        </div>
      )}

      {/* Summary Stats */}
      {documents.length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary Statistics</h3>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">{documents.length}</div>
              <div className="text-sm text-gray-600">Total Documents</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-danger-600">
                {documents.filter(doc => getRiskLevel(doc.risk_score) === 'high' || getRiskLevel(doc.risk_score) === 'critical').length}
              </div>
              <div className="text-sm text-gray-600">High Risk</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning-600">
                {documents.reduce((sum, doc) => sum + doc.anomaly_count, 0)}
              </div>
              <div className="text-sm text-gray-600">Total Anomalies</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {(documents.reduce((sum, doc) => sum + doc.risk_score, 0) / documents.length).toFixed(1)}
              </div>
              <div className="text-sm text-gray-600">Avg Risk Score</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Documents;
