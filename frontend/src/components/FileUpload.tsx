import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentIcon, XMarkIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { apiService } from '../services/api';
import { useAnalysis } from '../context/AnalysisContext';
import { useNavigate } from 'react-router-dom';

const FileUpload: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const { setCurrentAnalysis, setIsLoading } = useAnalysis();
  const navigate = useNavigate();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
      'text/csv',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    ];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Please upload a PDF, DOCX, CSV, or XLSX file');
      return;
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      toast.error('File size must be less than 50MB');
      return;
    }

    setUploading(true);
    setIsLoading(true);

    try {
      const result = await apiService.uploadDocument(file);
      setCurrentAnalysis(result);
      toast.success('Document analyzed successfully!');
      navigate(`/analysis/${result.document_id}`);
    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Failed to analyze document');
    } finally {
      setUploading(false);
      setIsLoading(false);
    }
  }, [setCurrentAnalysis, setIsLoading, navigate]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    multiple: false,
    disabled: uploading,
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer ${
          isDragActive
            ? 'border-primary-400 bg-primary-50'
            : uploading
            ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
            : 'border-gray-300 hover:border-primary-400 hover:bg-primary-50'
        }`}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center justify-center space-y-4">
          {uploading ? (
            <>
              <div className="loading-spinner w-8 h-8 text-primary-600"></div>
              <div className="space-y-2">
                <p className="text-lg font-medium text-gray-900">Analyzing Document...</p>
                <p className="text-sm text-gray-500">
                  This may take a few moments depending on document complexity
                </p>
              </div>
            </>
          ) : (
            <>
              <CloudArrowUpIcon className="w-12 h-12 text-gray-400" />
              <div className="space-y-2">
                <p className="text-lg font-medium text-gray-900">
                  {isDragActive ? 'Drop your document here' : 'Upload Financial Document'}
                </p>
                <p className="text-sm text-gray-500">
                  Drag and drop or click to select • PDF, PNG, JPG up to 50MB
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 text-xs text-gray-400">
                <span className="flex items-center">
                  <DocumentIcon className="w-4 h-4 mr-1" />
                  Bank Statements
                </span>
                <span className="flex items-center">
                  <DocumentIcon className="w-4 h-4 mr-1" />
                  Invoices
                </span>
                <span className="flex items-center">
                  <DocumentIcon className="w-4 h-4 mr-1" />
                  Financial Reports
                </span>
              </div>
            </>
          )}
        </div>

        {uploading && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-xl">
            <div className="text-center">
              <div className="loading-spinner w-8 h-8 text-primary-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">Processing...</p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 text-center">
        <p className="text-xs text-gray-500">
          Your documents are processed securely and not stored permanently
        </p>
      </div>
    </div>
  );
};

export default FileUpload;
