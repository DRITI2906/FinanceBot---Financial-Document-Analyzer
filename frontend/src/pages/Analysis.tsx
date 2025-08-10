import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAnalysis } from '../context/AnalysisContext';
import RiskBadge from '../components/RiskBadge';
import AnalysisChat from '../components/AnalysisChat';
import { 
  ArrowLeftIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CurrencyRupeeIcon,
  CalendarIcon,
  ChartBarIcon,
  ListBulletIcon
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import { AnalysisResult, Transaction, Anomaly } from '../types';

const Analysis: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const { currentAnalysis } = useAnalysis();
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'anomalies' | 'chat'>('overview');

  if (!currentAnalysis || currentAnalysis.document_id !== documentId) {
    return (
      <div className="text-center py-12">
        <DocumentTextIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Document Not Found</h2>
        <p className="text-gray-600 mb-6">The requested analysis could not be found.</p>
        <Link to="/" className="btn-primary">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const getRiskLevel = (score: number): 'low' | 'medium' | 'high' | 'critical' => {
    if (score >= 8) return 'critical';
    if (score >= 6) return 'high';
    if (score >= 3) return 'medium';
    return 'low';
  };

  const tabs = [
    { id: 'overview', name: 'Overview', icon: ChartBarIcon },
    { id: 'transactions', name: 'Transactions', icon: ListBulletIcon },
    { id: 'anomalies', name: 'Anomalies', icon: ExclamationTriangleIcon },
    { id: 'chat', name: 'Ask AI', icon: DocumentTextIcon },
  ];

  const StatCard: React.FC<{ 
    title: string; 
    value: string | number; 
    icon: React.ElementType; 
    color?: string;
  }> = ({ title, value, icon: Icon, color = 'text-primary-600' }) => (
    <div className="bg-white p-6 rounded-lg border border-gray-200">
      <div className="flex items-center">
        <Icon className={`w-8 h-8 ${color} mr-3`} />
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );

  const TransactionRow: React.FC<{ transaction: Transaction; index: number }> = ({ transaction, index }) => (
    <motion.tr
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="hover:bg-gray-50"
    >
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {transaction.date}
      </td>
      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
        {transaction.description}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm">
        <span className={`font-medium ${transaction.amount >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
          ₹{Math.abs(transaction.amount).toLocaleString()}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {transaction.category || '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {transaction.balance ? `₹${transaction.balance.toLocaleString()}` : '-'}
      </td>
    </motion.tr>
  );

  const AnomalyCard: React.FC<{ anomaly: Anomaly; index: number }> = ({ anomaly, index }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="bg-white p-6 rounded-lg border border-gray-200"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900 capitalize">
          {anomaly.type.replace('_', ' ')}
        </h3>
        <RiskBadge riskLevel={anomaly.risk_level} size="sm" />
      </div>
      <p className="text-gray-700 mb-3">{anomaly.description}</p>
      <div className="flex items-center text-sm text-gray-500">
        <span>Confidence: {(anomaly.confidence * 100).toFixed(0)}%</span>
      </div>
    </motion.div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeftIcon className="w-6 h-6" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{currentAnalysis.filename}</h1>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span className="capitalize">{currentAnalysis.document_type.replace('_', ' ')}</span>
              <span>•</span>
              <span>Processed {format(new Date(currentAnalysis.processed_at), 'MMM dd, yyyy HH:mm')}</span>
            </div>
          </div>
        </div>
        <RiskBadge riskLevel={getRiskLevel(currentAnalysis.risk_score)} size="lg" />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <StatCard
                title="Risk Score"
                value={`${currentAnalysis.risk_score.toFixed(1)}/10`}
                icon={ExclamationTriangleIcon}
                color={currentAnalysis.risk_score >= 7 ? 'text-danger-600' : 'text-warning-600'}
              />
              <StatCard
                title="Total Amount"
                value={`₹${Math.abs(currentAnalysis.summary.total_amount).toLocaleString()}`}
                icon={CurrencyRupeeIcon}
              />
              <StatCard
                title="Transactions"
                value={currentAnalysis.summary.total_transactions}
                icon={ListBulletIcon}
              />
              <StatCard
                title="Anomalies"
                value={currentAnalysis.anomalies.length}
                icon={ExclamationTriangleIcon}
                color={currentAnalysis.anomalies.length > 0 ? 'text-warning-600' : 'text-success-600'}
              />
            </div>

            {/* Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Key Insights */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Insights</h3>
                <ul className="space-y-2">
                  {currentAnalysis.summary.key_insights.map((insight, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-primary-600 rounded-full mt-2 flex-shrink-0"></div>
                      <span className="text-gray-700">{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommendations */}
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Recommendations</h3>
                <ul className="space-y-2">
                  {currentAnalysis.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-success-600 rounded-full mt-2 flex-shrink-0"></div>
                      <span className="text-gray-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'transactions' && (
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Transaction Details</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Category
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Balance
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {currentAnalysis.transactions.map((transaction, index) => (
                    <TransactionRow key={index} transaction={transaction} index={index} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'anomalies' && (
          <div className="space-y-4">
            {currentAnalysis.anomalies.length > 0 ? (
              currentAnalysis.anomalies.map((anomaly, index) => (
                <AnomalyCard key={index} anomaly={anomaly} index={index} />
              ))
            ) : (
              <div className="text-center py-12 card">
                <ExclamationTriangleIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Anomalies Detected</h3>
                <p className="text-gray-600">This document appears to have normal transaction patterns.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'chat' && (
          <AnalysisChat documentId={currentAnalysis.document_id} />
        )}
      </div>
    </div>
  );
};

export default Analysis;
