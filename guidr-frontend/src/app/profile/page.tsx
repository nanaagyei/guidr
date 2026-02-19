'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { getProfile, putProfile } from '@/utils/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import { CheckCircle2, AlertCircle } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState({
    country_of_citizenship: '',
    current_country: '',
    current_city: '',
    intended_degree: '',
    primary_field_of_study: '',
    secondary_fields: [] as string[],
    preferred_start_term: '',
    preferred_start_year: '',
    preferred_countries: [] as string[],
    preferred_cities: [] as string[],
    funding_priority: '',
    program_style_preference: '',
  });

  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadProfile();
  }, [user, router]);

  async function loadProfile() {
    try {
      const data = await getProfile();
      setProfile(data);
      setFormData({
        country_of_citizenship: data.country_of_citizenship || '',
        current_country: data.current_country || '',
        current_city: data.current_city || '',
        intended_degree: data.intended_degree || '',
        primary_field_of_study: data.primary_field_of_study || '',
        secondary_fields: data.secondary_fields || [],
        preferred_start_term: data.preferred_start_term || '',
        preferred_start_year: data.preferred_start_year || '',
        preferred_countries: data.preferred_countries || [],
        preferred_cities: data.preferred_cities || [],
        funding_priority: data.funding_priority || '',
        program_style_preference: data.program_style_preference || '',
      });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess(false);
    setSaving(true);

    try {
      const updated = await putProfile(formData);
      setProfile(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto flex items-center justify-center min-h-[400px]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full"
        />
      </div>
    );
  }

  const inputClasses = "input text-sm py-2.5";
  const labelClasses = "block text-sm font-medium text-textSecondary mb-1.5";

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-text mb-2">Profile</h1>
        <p className="text-textSecondary">Manage your personal and academic information.</p>
      </div>

      {profile && (
        <Card className="mb-6">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-textSecondary">Profile Completion</span>
              <span className="text-lg font-semibold text-text">{profile.profile_completion_score}%</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-500"
                style={{ width: `${profile.profile_completion_score}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

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

      {success && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-successLight border border-success/30 text-success px-4 py-3 rounded-xl mb-6 flex items-start gap-3"
        >
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <span>Profile updated successfully!</span>
        </motion.div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Basic Info</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelClasses}>
                Country of Citizenship
              </label>
              <input
                type="text"
                value={formData.country_of_citizenship}
                onChange={(e) => setFormData({ ...formData, country_of_citizenship: e.target.value })}
                className={inputClasses}
              />
            </div>
            <div>
              <label className={labelClasses}>
                Current Country
              </label>
              <input
                type="text"
                value={formData.current_country}
                onChange={(e) => setFormData({ ...formData, current_country: e.target.value })}
                className={inputClasses}
              />
            </div>
            <div>
              <label className={labelClasses}>
                Current City
              </label>
              <input
                type="text"
                value={formData.current_city}
                onChange={(e) => setFormData({ ...formData, current_city: e.target.value })}
                className={inputClasses}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Academic Interests</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className={labelClasses}>
                Intended Degree *
              </label>
              <select
                value={formData.intended_degree}
                onChange={(e) => setFormData({ ...formData, intended_degree: e.target.value })}
                className={inputClasses}
              >
                <option value="">Select degree</option>
                <option value="masters">Masters</option>
                <option value="phd">PhD</option>
              </select>
            </div>
            <div>
              <label className={labelClasses}>
                Primary Field of Study *
              </label>
              <input
                type="text"
                value={formData.primary_field_of_study}
                onChange={(e) => setFormData({ ...formData, primary_field_of_study: e.target.value })}
                placeholder="e.g., Computer Science"
                className={inputClasses}
              />
            </div>
            <div>
              <label className={labelClasses}>
                Secondary Fields (comma-separated)
              </label>
              <input
                type="text"
                value={formData.secondary_fields.join(', ')}
                onChange={(e) => setFormData({
                  ...formData,
                  secondary_fields: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                })}
                placeholder="e.g., Machine Learning, Data Science"
                className={inputClasses}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Location Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className={labelClasses}>
                Preferred Countries (comma-separated)
              </label>
              <input
                type="text"
                value={formData.preferred_countries.join(', ')}
                onChange={(e) => setFormData({
                  ...formData,
                  preferred_countries: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                })}
                placeholder="e.g., USA, Canada"
                className={inputClasses}
              />
            </div>
            <div>
              <label className={labelClasses}>
                Preferred Cities (comma-separated)
              </label>
              <input
                type="text"
                value={formData.preferred_cities.join(', ')}
                onChange={(e) => setFormData({
                  ...formData,
                  preferred_cities: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                })}
                placeholder="e.g., New York, Toronto"
                className={inputClasses}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Program Preferences</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={labelClasses}>
                Preferred Start Term
              </label>
              <select
                value={formData.preferred_start_term}
                onChange={(e) => setFormData({ ...formData, preferred_start_term: e.target.value })}
                className={inputClasses}
              >
                <option value="">Select term</option>
                <option value="fall">Fall</option>
                <option value="spring">Spring</option>
                <option value="summer">Summer</option>
                <option value="winter">Winter</option>
              </select>
            </div>
            <div>
              <label className={labelClasses}>
                Preferred Start Year
              </label>
              <input
                type="number"
                value={formData.preferred_start_year || ''}
                onChange={(e) => setFormData({ ...formData, preferred_start_year: e.target.value })}
                min={new Date().getFullYear()}
                className={inputClasses}
              />
            </div>
            <div>
              <label className={labelClasses}>
                Funding Priority
              </label>
              <select
                value={formData.funding_priority}
                onChange={(e) => setFormData({ ...formData, funding_priority: e.target.value })}
                className={inputClasses}
              >
                <option value="">Select priority</option>
                <option value="must_have">Must Have</option>
                <option value="nice_to_have">Nice to Have</option>
                <option value="no_preference">No Preference</option>
              </select>
            </div>
            <div>
              <label className={labelClasses}>
                Program Style Preference
              </label>
              <select
                value={formData.program_style_preference}
                onChange={(e) => setFormData({ ...formData, program_style_preference: e.target.value })}
                className={inputClasses}
              >
                <option value="">Select style</option>
                <option value="research">Research</option>
                <option value="coursework">Coursework</option>
                <option value="both">Both</option>
              </select>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" disabled={saving} size="lg">
          {saving ? 'Saving...' : 'Save Profile'}
        </Button>
      </form>
    </div>
  );
}

