'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  getEssay,
  updateEssay,
} from '@/utils/api';
import {
  ArrowLeft,
  Save,
  Eye,
  Loader2,
  CheckCircle2,
  FileText,
  History,
  Sparkles,
} from 'lucide-react';
import ReviewDisplay from '@/components/ReviewDisplay';

export default function EssayEditorPage() {
  const { user } = useAuth();
  const router = useRouter();
  const params = useParams();
  const essayId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [essay, setEssay] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isEditing, setIsEditing] = useState(true);
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const [wordCount, setWordCount] = useState(0);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showVersions, setShowVersions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    if (essayId !== 'new') {
      loadEssay();
    } else {
      setLoading(false);
      setIsEditing(true);
    }
  }, [user, router, essayId]);

  useEffect(() => {
    // Auto-save after 3 seconds of no typing
    if (essayId !== 'new' && content && title) {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }

      autoSaveTimerRef.current = setTimeout(() => {
        handleSave(true); // Silent save
      }, 3000);

      return () => {
        if (autoSaveTimerRef.current) {
          clearTimeout(autoSaveTimerRef.current);
        }
      };
    }
  }, [content, title]);

  useEffect(() => {
    if (content) {
      const words = content.trim().split(/\s+/).filter(word => word.length > 0);
      setWordCount(words.length);
    } else {
      setWordCount(0);
    }
  }, [content]);

  async function loadEssay() {
    try {
      const data = await getEssay(essayId, true, true);
      setEssay(data);
      setTitle(data.title || '');
      setContent(data.content || '');
      setWordCount(data.word_count || 0);
      setVersions(data.versions || []);
      setReviews(data.reviews || []);
      setError('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(isAutoSave = false) {
    if (!title.trim() || !content.trim()) {
      if (!isAutoSave) {
        setError('Title and content are required');
      }
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      await updateEssay(essayId, { title, content });
      if (!isAutoSave) {
        setSuccess('Essay saved!');
        setTimeout(() => setSuccess(''), 3000);
      }
      await loadEssay(); // Reload to get new version
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function loadVersion(versionNumber: number) {
    const version = versions.find(v => v.version_number === versionNumber);
    if (version) {
      setContent(version.content);
      setWordCount(version.word_count);
      setSelectedVersion(versionNumber);
      setIsEditing(false);
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

  if (essayId !== 'new' && error && !essay) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
          {error || 'Essay not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-text hover:text-gray-700 transition font-medium"
        >
          <ArrowLeft className="h-5 w-5" />
          Back
        </button>
        <div className="flex items-center gap-3">
          {essay && (
            // Essay feedback is gated pre-launch. The review flow (handleRequestReview,
            // ReviewDisplay) is preserved; re-enable once LLM feedback is wired.
            // See launch plan Workstream C.
            <button
              type="button"
              disabled
              title="AI essay feedback is coming soon"
              className="px-4 py-2 bg-gray-100 text-textMuted font-semibold rounded-lg cursor-not-allowed flex items-center gap-2"
            >
              <Sparkles className="h-4 w-4" />
              Review
              <span className="rounded-full bg-accent/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent">
                Soon
              </span>
            </button>
          )}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleSave()}
            disabled={saving || !title.trim() || !content.trim()}
            className="px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50 flex items-center gap-2"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save
              </>
            )}
          </motion.button>
        </div>
      </motion.div>

      {/* Messages */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-4"
          >
            {error}
          </motion.div>
        )}
        {success && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-4 flex items-center gap-2"
          >
            <CheckCircle2 className="h-5 w-5" />
            {success}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Editor */}
        <div className="lg:col-span-2 space-y-4">
          {/* Title */}
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Essay title..."
              className="w-full text-2xl font-semibold text-text bg-transparent border-none outline-none placeholder-gray-400"
            />
            {essay && (
              <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
                <span className="px-2.5 py-1 bg-primary/20 text-text rounded-lg text-xs font-medium capitalize">
                  {essay.essay_type?.replace('_', ' ')}
                </span>
                {selectedVersion && (
                  <span className="text-xs text-gray-500">
                    Version {selectedVersion}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Editor */}
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-text">Content</h3>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span className="font-medium">{wordCount.toLocaleString()} words</span>
                {saving && (
                  <span className="text-primary flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Auto-saving...
                  </span>
                )}
              </div>
            </div>
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Start writing your essay..."
              className="w-full h-[600px] p-4 bg-background rounded-lg border border-primary/20 focus:border-primary focus:ring-2 focus:ring-mustard/20 outline-none resize-none text-gray-700 leading-relaxed"
              disabled={!isEditing}
            />
          </div>

          {/* Latest Review */}
          {reviews.length > 0 && (
            <ReviewDisplay review={reviews[0]} />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Version History */}
          {versions.length > 0 && (
            <div className="bg-card rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-text flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Versions
                </h3>
                <button
                  onClick={() => setShowVersions(!showVersions)}
                  className="text-sm text-text hover:text-gray-700"
                >
                  {showVersions ? 'Hide' : 'Show'}
                </button>
              </div>
              {showVersions && (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {versions.map((version) => (
                    <motion.button
                      key={version.id}
                      whileHover={{ scale: 1.02 }}
                      onClick={() => loadVersion(version.version_number)}
                      className={`w-full text-left p-3 rounded-lg transition ${
                        selectedVersion === version.version_number
                          ? 'bg-primary/30 border-2 border-primary'
                          : 'bg-background/80 hover:bg-background border border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-text">
                          Version {version.version_number}
                        </span>
                        {selectedVersion === version.version_number && (
                          <Eye className="h-4 w-4 text-text" />
                        )}
                      </div>
                      <p className="text-xs text-gray-600 mt-1">
                        {version.word_count.toLocaleString()} words
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(version.created_at).toLocaleDateString()}
                      </p>
                    </motion.button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* All Reviews */}
          {reviews.length > 1 && (
            <div className="bg-card rounded-xl p-6 shadow-sm">
              <h3 className="font-semibold text-text mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5" />
                All Reviews ({reviews.length})
              </h3>
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {reviews.slice(1).map((review, index) => (
                  <button
                    key={review.id}
                    onClick={() => router.push(`/essays/${essayId}/review/${review.id}`)}
                    className="w-full text-left p-3 bg-background/80 rounded-lg hover:bg-background transition border border-transparent hover:border-primary/20"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-text">Review #{reviews.length - index}</span>
                      {review.overall_score !== undefined && (
                        <span className="text-sm font-semibold text-green-600">
                          {review.overall_score.toFixed(1)}/10
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {new Date(review.created_at).toLocaleDateString()}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
