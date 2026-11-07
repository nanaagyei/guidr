'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import {
  getAcademicRecords,
  postAcademicRecord,
  putAcademicRecord,
  deleteAcademicRecord,
} from '@/utils/api';
import { useToast } from '@/contexts/ToastContext';
import { useProfileCompletion } from '@/contexts/ProfileCompletionContext';

export default function AcademicRecordsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();
  const { completion, refresh: refreshCompletion } = useProfileCompletion();
  const prevLevelRef = useRef<number>(completion?.level ?? 0);

  // Toast when profile level increases
  useEffect(() => {
    const currentLevel = completion?.level ?? 0;
    if (currentLevel > prevLevelRef.current && prevLevelRef.current >= 0) {
      const unlockMessages: Record<number, string> = {
        1: 'Level 1 unlocked! Dashboard is now available.',
        2: 'Level 2 unlocked! Recommendations and Professors are now available.',
        3: 'Level 3 unlocked! Professor matching and email generation are now available.',
      };
      addToast(unlockMessages[currentLevel] || `Level ${currentLevel} unlocked!`, 'success');
    }
    prevLevelRef.current = currentLevel;
  }, [completion?.level, addToast]);
  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState<any[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    institution_name: '',
    country: '',
    degree_level: '',
    field_of_study: '',
    gpa_value: '',
    gpa_scale: '',
    start_year: '',
    end_year: '',
    is_current: false,
    notes: '',
  });

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadRecords();
  }, [user, router]);

  async function loadRecords() {
    try {
      const data = await getAcademicRecords();
      setRecords(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function openEditModal(record: any) {
    setEditingId(record.id);
    setFormData({
      institution_name: record.institution_name || '',
      country: record.country || '',
      degree_level: record.degree_level || '',
      field_of_study: record.field_of_study || '',
      gpa_value: record.gpa_value ? String(record.gpa_value) : '',
      gpa_scale: record.gpa_scale ? String(record.gpa_scale) : '',
      start_year: record.start_year ? String(record.start_year) : '',
      end_year: record.end_year ? String(record.end_year) : '',
      is_current: record.is_current || false,
      notes: record.notes || '',
    });
    setShowModal(true);
  }

  function resetForm() {
    setEditingId(null);
    setFormData({
      institution_name: '',
      country: '',
      degree_level: '',
      field_of_study: '',
      gpa_value: '',
      gpa_scale: '',
      start_year: '',
      end_year: '',
      is_current: false,
      notes: '',
    });
    setShowModal(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    try {
      const data = {
        ...formData,
        gpa_value: formData.gpa_value ? parseFloat(formData.gpa_value) : null,
        gpa_scale: formData.gpa_scale ? parseFloat(formData.gpa_scale) : null,
        start_year: formData.start_year ? parseInt(formData.start_year) : null,
        end_year: formData.end_year ? parseInt(formData.end_year) : null,
      };
      if (editingId) {
        await putAcademicRecord(editingId, data);
      } else {
        await postAcademicRecord(data);
      }
      resetForm();
      await loadRecords();
      await refreshCompletion();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Are you sure you want to delete this record?')) {
      return;
    }

    try {
      await deleteAcademicRecord(id);
      await loadRecords();
      await refreshCompletion();
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (loading) {
    return <div className="max-w-4xl mx-auto">Loading...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-semibold text-text">Academic Records</h1>
        <div className="flex gap-3">
          <button
            onClick={() => { setEditingId(null); resetForm(); setShowModal(true); }}
            className="px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
          >
            Add Manually
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {records.length === 0 ? (
        <div className="bg-card rounded-xl p-8 text-center">
          <p className="text-gray-700 mb-4">No academic records yet.</p>
          <button
            onClick={() => setShowModal(true)}
            className="px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
          >
            Add Your First Record
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {records.map((record) => (
            <div key={record.id} className="bg-card rounded-xl p-6 shadow-sm">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-semibold text-text mb-2">
                    {record.institution_name}
                  </h3>
                  <div className="space-y-1 text-gray-700">
                    <p><strong>Degree:</strong> {record.degree_level} in {record.field_of_study || 'N/A'}</p>
                    <p><strong>Location:</strong> {record.country}</p>
                    {record.normalized_gpa && (
                      <p><strong>GPA:</strong> {parseFloat(record.normalized_gpa).toFixed(2)} / 4.0</p>
                    )}
                    {record.start_year && record.end_year && (
                      <p><strong>Years:</strong> {record.start_year} - {record.end_year}</p>
                    )}
                    {record.is_current && (
                      <span className="inline-block px-2 py-1 bg-primary text-white text-xs font-semibold rounded">
                        Current
                      </span>
                    )}
                    {record.source === 'transcript_extraction' && (
                      <span className="inline-block px-2 py-1 bg-gray-700 text-eggshell text-xs font-semibold rounded ml-2">
                        From Transcript
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => openEditModal(record)}
                    className="text-primary hover:text-primaryHover font-medium"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(record.id)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-semibold mb-4 text-text">{editingId ? 'Edit Academic Record' : 'Add Academic Record'}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Institution Name *
                  </label>
                  <input
                    type="text"
                    value={formData.institution_name}
                    onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Country *
                  </label>
                  <input
                    type="text"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Degree Level *
                  </label>
                  <select
                    value={formData.degree_level}
                    onChange={(e) => setFormData({ ...formData, degree_level: e.target.value })}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  >
                    <option value="">Select degree</option>
                    <option value="bachelors">Bachelors</option>
                    <option value="masters">Masters</option>
                    <option value="phd">PhD</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Field of Study
                  </label>
                  <input
                    type="text"
                    value={formData.field_of_study}
                    onChange={(e) => setFormData({ ...formData, field_of_study: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    GPA Value
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.gpa_value}
                    onChange={(e) => setFormData({ ...formData, gpa_value: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    GPA Scale
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.gpa_scale}
                    onChange={(e) => setFormData({ ...formData, gpa_scale: e.target.value })}
                    placeholder="e.g., 4.0, 10.0"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Start Year
                  </label>
                  <input
                    type="number"
                    value={formData.start_year}
                    onChange={(e) => setFormData({ ...formData, start_year: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    End Year
                  </label>
                  <input
                    type="number"
                    value={formData.end_year}
                    onChange={(e) => setFormData({ ...formData, end_year: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                  />
                </div>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_current"
                  checked={formData.is_current}
                  onChange={(e) => setFormData({ ...formData, is_current: e.target.checked })}
                  className="mr-2"
                />
                <label htmlFor="is_current" className="text-sm text-gray-700">
                  Currently enrolled
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mustard"
                />
              </div>
              <div className="flex gap-4">
                <button
                  type="submit"
                  className="px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
