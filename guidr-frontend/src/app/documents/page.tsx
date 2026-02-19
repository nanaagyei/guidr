'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import {
  getDocuments,
  getDocumentUploadUrl,
  confirmDocumentUpload,
  deleteDocument,
} from '@/utils/api';
import DocumentUpload from '@/components/DocumentUpload';
import DocumentCard from '@/components/DocumentCard';
import { Button } from '@/components/ui/button';
import { Upload, FileText, AlertCircle } from 'lucide-react';

export default function DocumentsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [documents, setDocuments] = useState<any[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadDocuments();
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [user, router]);

  // Poll for processing status updates
  useEffect(() => {
    const hasProcessingDocuments = documents.some(
      (doc) => doc.processing_status === 'pending' || doc.processing_status === 'processing'
    );

    if (hasProcessingDocuments && !pollingIntervalRef.current) {
      pollingIntervalRef.current = setInterval(() => {
        loadDocuments();
      }, 3000); // Poll every 3 seconds
    } else if (!hasProcessingDocuments && pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [documents]);

  async function loadDocuments() {
    try {
      const data = await getDocuments();
      setDocuments(data);
      setError('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file: File, documentType: string) {
    setUploading(true);
    setError('');

    try {
      // Step 1: Get upload URL
      const { upload_url, document_id } = await getDocumentUploadUrl({
        filename: file.name,
        document_type: documentType,
      });

      // Step 2: Upload file to R2
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type,
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Failed to upload file to storage');
      }

      // Step 3: Confirm upload
      await confirmDocumentUpload(document_id);

      // Step 4: Reload documents
      setShowUploadModal(false);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
      throw err;
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteDocument(id);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
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

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-text mb-2">Documents</h1>
          <p className="text-textSecondary">Manage your transcripts, resumes, and essays</p>
        </div>
        <Button onClick={() => setShowUploadModal(true)} size="lg">
          <Upload className="h-5 w-5" />
          Upload Document
        </Button>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-errorLight border border-error/30 text-error px-4 py-3 rounded-xl mb-6 flex items-start gap-3"
        >
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </motion.div>
      )}

      {documents.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-card rounded-xl p-12 text-center border-2 border-dashed border-primary/20"
        >
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="flex justify-center mb-4"
          >
            <FileText className="h-16 w-16 text-text/40" />
          </motion.div>
          <p className="text-lg text-text mb-2 font-medium">No documents uploaded yet</p>
          <p className="text-sm text-textSecondary mb-6">
            Upload your transcripts, resumes, or essays to get started
          </p>
          <Button onClick={() => setShowUploadModal(true)} size="lg">
            <Upload className="h-5 w-5" />
            Upload Your First Document
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {documents.map((doc, index) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDelete={handleDelete}
              index={index}
            />
          ))}
        </div>
      )}

      {showUploadModal && (
        <DocumentUpload
          onUpload={handleUpload}
          onClose={() => {
            setShowUploadModal(false);
            setError('');
          }}
          uploading={uploading}
          error={error}
        />
      )}
    </div>
  );
}

