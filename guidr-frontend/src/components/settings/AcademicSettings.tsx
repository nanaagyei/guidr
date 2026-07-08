'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { DashboardCard } from '../ui/dashboard-card';
import { GraduationCap, ArrowRight, Plus } from 'lucide-react';
import { getAcademicRecords } from '@/utils/api';

export default function AcademicSettings() {
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadRecords = async () => {
      setLoading(true);
      try {
        const data = await getAcademicRecords();
        setRecords(data);
      } catch (error) {
        console.error('Failed to load academic records:', error);
      } finally {
        setLoading(false);
      }
    };

    loadRecords();
  }, []);

  return (
    <DashboardCard>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded-lg">
          <GraduationCap className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-text">Academic Settings</h2>
          <p className="text-sm text-gray-600">Manage your academic records and preferences</p>
        </div>
      </div>

      <div className="space-y-6">
        {/* Academic Records */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text">Academic Records</h3>
            <Link
              href="/academic-records"
              className="text-sm text-primary hover:text-primaryHover font-medium inline-flex items-center gap-1"
            >
              Manage Records
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : records.length === 0 ? (
            <div className="p-6 border-2 border-dashed border-gray-300 rounded-lg text-center">
              <p className="text-sm text-gray-600 mb-3">No academic records yet</p>
              <Link
                href="/academic-records"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition text-sm"
              >
                <Plus className="h-4 w-4" />
                Add Academic Record
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {records.map((record) => (
                <div
                  key={record.id}
                  className="p-4 border border-border rounded-lg hover:border-primary/30 transition-colors"
                >
                  <h4 className="font-semibold text-text mb-1">{record.institution_name}</h4>
                  <p className="text-sm text-gray-600">
                    {record.degree_level} • {record.field_of_study}
                  </p>
                  {record.gpa_value && (
                    <p className="text-sm text-gray-500 mt-1">
                      GPA: {record.gpa_value} / {record.gpa_scale}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Preferences Section */}
        <div className="pt-6 border-t border-border">
          <h3 className="font-semibold text-text mb-4">Degree Preferences</h3>
          <Link
            href="/profile"
            className="text-sm text-primary hover:text-primaryHover font-medium inline-flex items-center gap-1"
          >
            Update preferences in your profile
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </DashboardCard>
  );
}
