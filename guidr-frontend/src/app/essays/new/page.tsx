'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import { createEssay, getDocument } from '@/utils/api';
import {
  ArrowLeft,
  Loader2,
  FileText,
} from 'lucide-react';

export default function NewEssayPage() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const documentId = searchParams.get('document_id');

  const [loading, setLoading] = useState(false);
  const [loadingDocument, setLoadingDocument] = useState(!!documentId);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    essay_type: 'personal_statement',
    content: '',
    target_program_id: '',
  });

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    if (documentId) {
      loadDocument();
    }
  }, [user, router, documentId]);

  async function loadDocument() {
    try {
      const doc = await getDocument(documentId!);
      if (doc.extracted_summary?.text) {
        setFormData(prev => ({
          ...prev,
          content: doc.extracted_summary.text,
          title: doc.original_filename.replace(/\.(pdf|doc|docx|txt)$/i, ''),
        }));
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoadingDocument(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.title.trim() || !formData.content.trim()) {
      setError('Title and content are required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const essay = await createEssay(formData);
      router.push(`/essays/${essay.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loadingDocument) {
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

  return (
    <div className="max-w-3xl mx-auto">
      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        onClick={() => router.back()}
        className="mb-6 flex items-center gap-2 text-text hover:text-gray-700 transition font-medium"
      >
        <ArrowLeft className="h-5 w-5" />
        Back
      </motion.button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-card rounded-xl p-8 shadow-sm"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary/20 rounded-lg">
            <FileText className="h-6 w-6 text-text" />
          </div>
          <h1 className="text-2xl font-semibold text-text">Create New Essay</h1>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Essay Title *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g., Personal Statement for Stanford"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard focus:border-transparent bg-white"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Essay Type *
            </label>
            <select
              value={formData.essay_type}
              onChange={(e) => setFormData({ ...formData, essay_type: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard focus:border-transparent bg-white"
              required
            >
              <option value="personal_statement">Personal Statement</option>
              <option value="sop">Statement of Purpose</option>
              <option value="diversity">Diversity Statement</option>
              <option value="why_school">Why School</option>
              <option value="research_statement">Research Statement</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Content *
            </label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              placeholder="Start writing your essay..."
              rows={15}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard focus:border-transparent bg-white resize-none"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              {formData.content.trim().split(/\s+/).filter(w => w.length > 0).length} words
            </p>
          </div>

          <div className="flex gap-4">
            <motion.button
              type="submit"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={loading || !formData.title.trim() || !formData.content.trim()}
              className="flex-1 px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Essay'
              )}
            </motion.button>
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition"
            >
              Cancel
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
