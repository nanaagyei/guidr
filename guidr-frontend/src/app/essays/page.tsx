'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import { getEssays, deleteEssay } from '@/utils/api';
import EssayCard from '@/components/EssayCard';
import { Button } from '@/components/ui/button';
import { PenTool, Plus, Filter, AlertCircle } from 'lucide-react';

export default function EssaysPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [essays, setEssays] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadEssays();
  }, [user, router]);

  async function loadEssays() {
    try {
      const data = await getEssays();
      setEssays(data);
      setError('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteEssay(id);
      await loadEssays();
    } catch (err: any) {
      setError(err.message);
    }
  }

  const filteredEssays = filterType === 'all'
    ? essays
    : essays.filter(essay => essay.essay_type === filterType);

  const essayTypes = [
    { value: 'all', label: 'All Essays' },
    { value: 'personal_statement', label: 'Personal Statement' },
    { value: 'sop', label: 'Statement of Purpose' },
    { value: 'diversity', label: 'Diversity Statement' },
    { value: 'why_school', label: 'Why School' },
    { value: 'research_statement', label: 'Research Statement' },
    { value: 'other', label: 'Other' },
  ];

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
          <h1 className="text-3xl font-semibold text-text mb-2">Essays</h1>
          <p className="text-textSecondary">Manage your application essays and get AI-powered reviews</p>
        </div>
        <Button onClick={() => router.push('/essays/new')} size="lg">
          <Plus className="h-5 w-5" />
          New Essay
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

      {/* Filter */}
      <div className="mb-6 flex items-center gap-4">
        <Filter className="h-5 w-5 text-text/60" />
        <div className="flex flex-wrap gap-2">
          {essayTypes.map((type) => (
            <button
              key={type.value}
              onClick={() => setFilterType(type.value)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                filterType === type.value
                  ? 'bg-primary text-white shadow-soft'
                  : 'bg-card text-textSecondary border border-border hover:bg-muted hover:text-text'
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {filteredEssays.length === 0 ? (
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
            <PenTool className="h-16 w-16 text-text/40" />
          </motion.div>
          <p className="text-lg text-text mb-2 font-medium">
            {filterType === 'all' ? 'No essays yet' : `No ${essayTypes.find(t => t.value === filterType)?.label.toLowerCase()} essays`}
          </p>
          <p className="text-sm text-textSecondary mb-6">
            Create your first essay to get started with AI-powered feedback
          </p>
          <Button onClick={() => router.push('/essays/new')} size="lg">
            <Plus className="h-5 w-5" />
            Create Your First Essay
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredEssays.map((essay, index) => (
            <EssayCard
              key={essay.id}
              essay={essay}
              onDelete={handleDelete}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}

