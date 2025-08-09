import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import FileUpload from '../components/FileUpload';
import RiskBadge from '../components/RiskBadge';
import { ProcessedDocument } from '../types';
import { apiService } from '../services/api';
import { 
  DocumentTextIcon, 
  ChartBarIcon, 
  ExclamationTriangleIcon,
  ClockIcon 
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const [recentDocuments, setRecentDocuments] = useState<ProcessedDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalDocuments: 0,
    highRiskCount: 0,
    avgRiskScore: 0,
  });

  useEffect(() => {
    loadRecentDocuments();
  }, []);

  const loadRecentDocuments = async () => {
    try {
      const response = await apiService.getDocuments();
      const documents = response.documents || [];
      setRecentDocuments(documents.slice(0, 5)); // Show only recent 5

      // Calculate stats
      setStats({
        totalDocuments: documents.length,
        highRiskCount: documents.filter(doc => doc.risk_score >= 7).length,
        avgRiskScore: documents.length > 0 
          ? documents.reduce((sum, doc) => sum + doc.risk_score, 0) / documents.length 
          : 0,
      });
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

  const StatCard: React.FC<{ 
    title: string; 
    value: string | number; 
    icon: React.ElementType; 
    color: string;
    subtitle?: string;
  }> = ({ title, value, icon: Icon, color, subtitle }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
    >
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-500">{subtitle}</p>
          )}
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-bold text-gray-900"
        >
          Finance Document Analyzer
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-2 text-lg text-gray-600"
        >
          Upload your financial documents for AI-powered analysis and fraud detection
        </motion.p>
      </div>

      {/* Stats Cards */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        <StatCard
          title="Total Documents"
          value={stats.totalDocuments}
          icon={DocumentTextIcon}
          color="bg-primary-500"
        />
        <StatCard
          title="High Risk Alerts"
          value={stats.highRiskCount}
          icon={ExclamationTriangleIcon}
          color="bg-danger-500"
        />
        <StatCard
          title="Average Risk Score"
          value={stats.avgRiskScore.toFixed(1)}
          icon={ChartBarIcon}
          color="bg-warning-500"
          subtitle="out of 10"
        />
      </motion.div>

      {/* Main Upload Area */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card"
      >
        <FileUpload />
      </motion.div>

      {/* Recent Documents */}
      {recentDocuments.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Recent Documents</h2>
            <Link 
              to="/documents" 
              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              View all →
            </Link>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="loading-spinner w-6 h-6 text-primary-600"></div>
              <span className="ml-2 text-gray-600">Loading documents...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {recentDocuments.map((doc, index) => (
                <motion.div
                  key={doc.document_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center space-x-4">
                    <DocumentTextIcon className="w-8 h-8 text-gray-400" />
                    <div>
                      <h3 className="font-medium text-gray-900">{doc.filename}</h3>
                      <div className="flex items-center space-x-2 text-sm text-gray-500">
                        <span className="capitalize">{doc.document_type.replace('_', ' ')}</span>
                        <span>•</span>
                        <span>{doc.transaction_count} transactions</span>
                        {doc.anomaly_count > 0 && (
                          <>
                            <span>•</span>
                            <span className="text-warning-600">{doc.anomaly_count} anomalies</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <RiskBadge riskLevel={getRiskLevel(doc.risk_score)} size="sm" />
                    <Link
                      to={`/analysis/${doc.document_id}`}
                      className="btn-primary text-sm"
                    >
                      View Analysis
                    </Link>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* Features Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {[
          {
            title: 'Smart Document Parsing',
            description: 'Automatically extract data from PDFs and images using advanced OCR and AI',
            icon: DocumentTextIcon,
          },
          {
            title: 'Fraud Detection',
            description: 'Identify suspicious patterns, duplicates, and high-risk transactions',
            icon: ExclamationTriangleIcon,
          },
          {
            title: 'Risk Analysis',
            description: 'Get comprehensive risk scores and actionable recommendations',
            icon: ChartBarIcon,
          },
        ].map((feature, index) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 + (0.1 * index) }}
            className="text-center p-6 bg-white rounded-xl border border-gray-200"
          >
            <feature.icon className="w-12 h-12 text-primary-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
            <p className="text-gray-600">{feature.description}</p>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
};

export default Dashboard;
