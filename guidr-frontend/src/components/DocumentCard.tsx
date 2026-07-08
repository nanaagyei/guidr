'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { FileText, Clock, CheckCircle2, XCircle, Loader2, Trash2, Eye } from 'lucide-react';
import { useState } from 'react';

interface DocumentCardProps {
  document: {
    id: string;
    original_filename: string;
    document_type: string;
    processing_status: 'pending' | 'processing' | 'completed' | 'failed';
    uploaded_at: string;
    processed_at?: string;
    processing_error_message?: string;
    file_size_bytes?: number;
    extracted_summary?: any;
  };
  onDelete?: (id: string) => void;
  index?: number;
}

export default function DocumentCard({ document, onDelete, index = 0 }: DocumentCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          color: 'bg-green-100 text-green-800 border-green-200',
          icon: CheckCircle2,
          label: 'Completed',
        };
      case 'processing':
        return {
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          icon: Loader2,
          label: 'Processing',
        };
      case 'failed':
        return {
          color: 'bg-red-100 text-red-800 border-red-200',
          icon: XCircle,
          label: 'Failed',
        };
      default:
        return {
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          icon: Clock,
          label: 'Pending',
        };
    }
  };

  const statusConfig = getStatusConfig(document.processing_status);
  const StatusIcon = statusConfig.icon;

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown size';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const getDocumentTypeColor = (type: string) => {
    switch (type) {
      case 'transcript':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'resume':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'essay':
        return 'bg-green-100 text-green-700 border-green-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const handleDelete = async () => {
    if (!onDelete || !confirm('Are you sure you want to delete this document?')) {
      return;
    }
    setIsDeleting(true);
    try {
      await onDelete(document.id);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ scale: 1.02 }}
      className="bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition-all border border-border hover:border-primary/30"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-text truncate">{document.original_filename}</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {formatFileSize(document.file_size_bytes)} • Uploaded {new Date(document.uploaded_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          {/* Status and Type Badges */}
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <motion.div
              whileHover={{ scale: 1.05 }}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border ${statusConfig.color}`}
            >
              {document.processing_status === 'processing' ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <StatusIcon className="h-3.5 w-3.5" />
                </motion.div>
              ) : (
                <StatusIcon className="h-3.5 w-3.5" />
              )}
              {statusConfig.label}
            </motion.div>

            <span className={`px-3 py-1 rounded-lg text-xs font-semibold border capitalize ${getDocumentTypeColor(document.document_type)}`}>
              {document.document_type}
            </span>
          </div>

          {/* Extracted Summary Preview */}
          {document.extracted_summary && document.document_type === 'transcript' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 p-3 bg-muted rounded-lg border border-border"
            >
              <p className="text-xs font-medium text-text mb-1.5">Extracted Data:</p>
              <div className="text-xs text-gray-700 space-y-1">
                {document.extracted_summary.gpa_value && (
                  <p>
                    <span className="font-medium">GPA:</span> {document.extracted_summary.gpa_value} / {document.extracted_summary.gpa_scale}
                  </p>
                )}
                {document.extracted_summary.institution_name && (
                  <p>
                    <span className="font-medium">Institution:</span> {document.extracted_summary.institution_name}
                  </p>
                )}
              </div>
            </motion.div>
          )}

          {/* Error Message */}
          {document.processing_error_message && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700"
            >
              <p className="font-medium">Error:</p>
              <p>{document.processing_error_message}</p>
            </motion.div>
          )}

          {/* Processed Date */}
          {document.processed_at && (
            <p className="text-xs text-gray-500 mt-2">
              Processed {new Date(document.processed_at).toLocaleDateString()}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <Link
            href={`/documents/${document.id}`}
            className="p-2 bg-primary text-white rounded-lg hover:bg-primaryHover transition-colors flex items-center justify-center group"
            title="View document"
          >
            <Eye className="h-4 w-4 group-hover:scale-110 transition-transform" />
          </Link>
          {onDelete && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleDelete}
              disabled={isDeleting}
              className="p-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors disabled:opacity-50 flex items-center justify-center"
              title="Delete document"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
