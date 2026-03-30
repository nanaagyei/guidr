/**
 * Mock data utilities for features without backend endpoints yet.
 * These will be replaced with actual API calls once backend is implemented.
 */

export interface MockDeadline {
  id: string;
  school_name: string;
  program_name: string;
  deadline_date: string;
  days_until: number;
  urgency: 'high' | 'medium' | 'low';
}

export interface MockSavedSchool {
  id: string;
  name: string;
  location: string;
  country: string;
  program_count: number;
  saved_date: string;
}

export interface MockAppliedSchool {
  id: string;
  school_name: string;
  program_name: string;
  status: 'applied' | 'interested' | 'in_progress';
  application_deadline?: string;
  applied_date?: string;
}

export interface MockProfessor {
  id: string;
  full_name: string;
  title?: string;
  school_name: string;
  school_id: string;
  research_area: string;
  department?: string;
}

/**
 * Get mock calendar deadlines
 */
export function getMockDeadlines(): MockDeadline[] {
  const today = new Date();
  const deadlines: MockDeadline[] = [
    {
      id: '1',
      school_name: 'MIT',
      program_name: 'Computer Science PhD',
      deadline_date: new Date(today.getTime() + 5 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      days_until: 5,
      urgency: 'high',
    },
    {
      id: '2',
      school_name: 'Stanford University',
      program_name: 'Electrical Engineering MS',
      deadline_date: new Date(today.getTime() + 12 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      days_until: 12,
      urgency: 'medium',
    },
    {
      id: '3',
      school_name: 'UC Berkeley',
      program_name: 'Data Science Masters',
      deadline_date: new Date(today.getTime() + 25 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      days_until: 25,
      urgency: 'medium',
    },
    {
      id: '4',
      school_name: 'Carnegie Mellon',
      program_name: 'Machine Learning PhD',
      deadline_date: new Date(today.getTime() + 45 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      days_until: 45,
      urgency: 'low',
    },
  ];

  return deadlines.sort((a, b) => a.days_until - b.days_until);
}

/**
 * Get mock saved schools
 */
export function getMockSavedSchools(): MockSavedSchool[] {
  return [
    {
      id: '1',
      name: 'MIT',
      location: 'Cambridge, MA',
      country: 'USA',
      program_count: 12,
      saved_date: '2024-01-15',
    },
    {
      id: '2',
      name: 'Stanford University',
      location: 'Stanford, CA',
      country: 'USA',
      program_count: 8,
      saved_date: '2024-01-20',
    },
    {
      id: '3',
      name: 'UC Berkeley',
      location: 'Berkeley, CA',
      country: 'USA',
      program_count: 15,
      saved_date: '2024-01-22',
    },
  ];
}

/**
 * Get mock applied schools
 */
export function getMockAppliedSchools(): MockAppliedSchool[] {
  const today = new Date();
  return [
    {
      id: '1',
      school_name: 'MIT',
      program_name: 'Computer Science PhD',
      status: 'applied',
      applied_date: '2024-01-10',
      application_deadline: new Date(today.getTime() + 5 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    },
    {
      id: '2',
      school_name: 'Stanford University',
      program_name: 'Electrical Engineering MS',
      status: 'in_progress',
      application_deadline: new Date(today.getTime() + 12 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    },
    {
      id: '3',
      school_name: 'UC Berkeley',
      program_name: 'Data Science Masters',
      status: 'interested',
      application_deadline: new Date(today.getTime() + 25 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    },
  ];
}

/**
 * Get mock recommended professors
 */
export function getMockProfessors(): MockProfessor[] {
  return [
    {
      id: '1',
      full_name: 'Dr. Jane Smith',
      title: 'Associate Professor',
      school_name: 'MIT',
      school_id: 'mit-1',
      research_area: 'Machine Learning & Deep Learning',
      department: 'Computer Science',
    },
    {
      id: '2',
      full_name: 'Dr. John Doe',
      title: 'Professor',
      school_name: 'Stanford University',
      school_id: 'stanford-1',
      research_area: 'Natural Language Processing',
      department: 'Computer Science',
    },
    {
      id: '3',
      full_name: 'Dr. Sarah Johnson',
      title: 'Assistant Professor',
      school_name: 'UC Berkeley',
      school_id: 'berkeley-1',
      research_area: 'Computer Vision',
      department: 'Electrical Engineering',
    },
  ];
}

/**
 * Mock tips/help content
 */
export interface HelpTip {
  id: string;
  title: string;
  content: string;
  category: 'getting-started' | 'applications' | 'essays' | 'recommendations';
}

export function getMockTips(): HelpTip[] {
  return [
    {
      id: '1',
      title: 'Complete Your Profile',
      content: 'Add your academic background and preferences to get personalized program recommendations.',
      category: 'getting-started',
    },
    {
      id: '2',
      title: 'Start Early on Essays',
      content: 'Begin drafting your application essays at least 2-3 months before deadlines.',
      category: 'essays',
    },
    {
      id: '3',
      title: 'Track Deadlines',
      content: 'Keep track of all application deadlines to avoid missing important dates.',
      category: 'applications',
    },
  ];
}

