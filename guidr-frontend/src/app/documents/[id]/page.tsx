'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { getDocument } from '@/utils/api';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  Clock,
  XCircle,
  Loader2,
  Calendar,
  HardDrive,
  FileType,
  Download,
} from 'lucide-react';

export default function DocumentDetailPage() {
  const { user } = useAuth();
  const router = useRouter();
  const params = useParams();
  const documentId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [document, setDocument] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadDocument();

    // Poll for status updates if processing
    const interval = setInterval(() => {
      if (document && (document.processing_status === 'pending' || document.processing_status === 'processing')) {
        loadDocument();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [user, router, documentId]);

  async function loadDocument() {
    try {
      const data = await getDocument(documentId);
      setDocument(data);
      setError('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-center min-h-[400px]">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full"
          />
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg"
        >
          {error || 'Document not found'}
        </motion.div>
      </div>
    );
  }

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

  return (
    <div className="max-w-5xl mx-auto">
      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        onClick={() => router.back()}
        className="mb-6 flex items-center gap-2 text-text hover:text-gray-700 transition font-medium"
      >
        <ArrowLeft className="h-5 w-5" />
        Back to Documents
      </motion.button>

      {/* Document Header Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-card rounded-xl p-6 mb-6 shadow-sm border border-primary/10"
      >
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-start gap-4 flex-1">
            <div className="p-3 bg-primary/20 rounded-xl">
              <FileText className="h-8 w-8 text-text" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-semibold text-text mb-3">{document.original_filename}</h1>
              <div className="flex flex-wrap items-center gap-2">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold border ${statusConfig.color}`}
                >
                  {document.processing_status === 'processing' ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >
                      <StatusIcon className="h-4 w-4" />
                    </motion.div>
                  ) : (
                    <StatusIcon className="h-4 w-4" />
                  )}
                  {statusConfig.label}
                </motion.div>
                <span className="px-3 py-1.5 bg-gray-700/20 text-gray-700 text-sm font-semibold rounded-lg border border-border/30 capitalize">
                  {document.document_type}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Document Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-primary/20">
          <div className="flex items-center gap-3 text-gray-700">
            <Calendar className="h-5 w-5 text-text/60" />
            <div>
              <p className="text-xs text-gray-500">Uploaded</p>
              <p className="font-medium">{new Date(document.uploaded_at).toLocaleString()}</p>
            </div>
          </div>
          {document.processed_at && (
            <div className="flex items-center gap-3 text-gray-700">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-xs text-gray-500">Processed</p>
                <p className="font-medium">{new Date(document.processed_at).toLocaleString()}</p>
              </div>
            </div>
          )}
          <div className="flex items-center gap-3 text-gray-700">
            <HardDrive className="h-5 w-5 text-text/60" />
            <div>
              <p className="text-xs text-gray-500">File Size</p>
              <p className="font-medium">{formatFileSize(document.file_size_bytes)}</p>
            </div>
          </div>
          {document.mime_type && (
            <div className="flex items-center gap-3 text-gray-700">
              <FileType className="h-5 w-5 text-text/60" />
              <div>
                <p className="text-xs text-gray-500">MIME Type</p>
                <p className="font-medium">{document.mime_type}</p>
              </div>
            </div>
          )}
        </div>

        {document.processing_error_message && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"
          >
            <div className="flex items-start gap-2">
              <XCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-800 mb-1">Processing Error</p>
                <p className="text-sm text-red-700">{document.processing_error_message}</p>
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>

      {/* Extracted Data Section */}
      {document.extracted_summary && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card rounded-xl p-6 mb-6 shadow-sm border border-primary/10"
        >
          <h2 className="text-xl font-semibold mb-4 text-text flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Extracted Data
          </h2>

          {document.document_type === 'transcript' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {document.extracted_summary.institution_name && (
                <div className="p-4 bg-background/80 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Institution</p>
                  <p className="font-semibold text-text">{document.extracted_summary.institution_name}</p>
                </div>
              )}
              {document.extracted_summary.gpa_value && (
                <div className="p-4 bg-background/80 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">GPA</p>
                  <p className="font-semibold text-text">
                    {document.extracted_summary.gpa_value} / {document.extracted_summary.gpa_scale}
                  </p>
                </div>
              )}
              {document.extracted_summary.degree_level && (
                <div className="p-4 bg-background/80 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Degree Level</p>
                  <p className="font-semibold text-text capitalize">{document.extracted_summary.degree_level}</p>
                </div>
              )}
              {document.extracted_summary.field_of_study && (
                <div className="p-4 bg-background/80 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Field of Study</p>
                  <p className="font-semibold text-text">{document.extracted_summary.field_of_study}</p>
                </div>
              )}
            </div>
          )}

          {document.document_type === 'resume' && document.extracted_summary.skills && (
            <div className="p-4 bg-background/80 rounded-lg">
              <p className="text-sm font-semibold text-text mb-3">Skills</p>
              <div className="flex flex-wrap gap-2">
                {document.extracted_summary.skills.map((skill: string, i: number) => (
                  <span
                    key={i}
                    className="px-3 py-1 bg-primary/30 text-text text-sm font-medium rounded-lg"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {document.document_type === 'essay' && document.extracted_summary.text && (
            <div className="p-4 bg-background/80 rounded-lg">
              <p className="text-sm font-semibold text-text mb-3">Extracted Text</p>
              <div className="prose max-w-none">
                <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {document.extracted_summary.text}
                </p>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Actions */}
      {document.document_type === 'essay' && document.extracted_summary && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex gap-4"
        >
          <motion.a
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            href={`/essays/new?document_id=${document.id}`}
            className="px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition inline-flex items-center gap-2 shadow-md"
          >
            <FileText className="h-5 w-5" />
            Create Essay from Document
          </motion.a>
        </motion.div>
      )}
    </div>
  );
}
