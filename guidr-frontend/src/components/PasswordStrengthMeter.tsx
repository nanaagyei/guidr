'use client';

import { useState, useEffect } from 'react';

interface PasswordStrengthMeterProps {
  password: string;
  onStrengthChange?: (strength: string, isValid: boolean) => void;
}

export default function PasswordStrengthMeter({ password, onStrengthChange }: PasswordStrengthMeterProps) {
  const [strength, setStrength] = useState<{
    score: number;
    strength: string;
    feedback: string[];
    requirements: {
      length: boolean;
      uppercase: boolean;
      lowercase: boolean;
      number: boolean;
      special: boolean;
    };
    is_valid: boolean;
  } | null>(null);

  useEffect(() => {
    if (!password) {
      setStrength(null);
      onStrengthChange?.('', false);
      return;
    }

    // Client-side strength check (simplified version)
    const checkStrength = () => {
      const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
      };

      let score = 0;
      const feedback: string[] = [];

      if (requirements.length) {
        if (password.length >= 12) score += 1;
        else score += 0.5;
      } else {
        feedback.push('At least 8 characters');
      }

      if (requirements.uppercase) score += 1;
      else feedback.push('Uppercase letter');
      if (requirements.lowercase) score += 1;
      else feedback.push('Lowercase letter');
      if (requirements.number) score += 1;
      else feedback.push('Number');
      if (requirements.special) score += 1;
      else feedback.push('Special character');

      const scoreInt = Math.floor(score);
      let strengthLevel = 'very_weak';
      if (scoreInt === 0) strengthLevel = 'very_weak';
      else if (scoreInt === 1) strengthLevel = 'weak';
      else if (scoreInt === 2) strengthLevel = 'fair';
      else if (scoreInt === 3) strengthLevel = 'good';
      else strengthLevel = 'very_strong';

      const is_valid = Object.values(requirements).every(v => v) && password.length >= 8;

      const result = {
        score: scoreInt,
        strength: strengthLevel,
        feedback: feedback.length > 0 ? feedback : ['Strong password!'],
        requirements,
        is_valid,
      };

      setStrength(result);
      onStrengthChange?.(strengthLevel, is_valid);
    };

    checkStrength();
  }, [password, onStrengthChange]);

  if (!password || !strength) return null;

  const getStrengthColor = () => {
    switch (strength.strength) {
      case 'very_weak': return 'bg-red-500';
      case 'weak': return 'bg-orange-500';
      case 'fair': return 'bg-yellow-500';
      case 'good': return 'bg-blue-500';
      case 'very_strong': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getStrengthLabel = () => {
    switch (strength.strength) {
      case 'very_weak': return 'Very Weak';
      case 'weak': return 'Weak';
      case 'fair': return 'Fair';
      case 'good': return 'Good';
      case 'very_strong': return 'Very Strong';
      default: return '';
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-700/20 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${getStrengthColor()}`}
            style={{ width: `${(strength.score / 4) * 100}%` }}
          />
        </div>
        <span className={`text-sm font-medium ${getStrengthColor().replace('bg-', 'text-')}`}>
          {getStrengthLabel()}
        </span>
      </div>

      <div className="text-xs text-gray-700/70 space-y-1">
        <div className="font-medium mb-1">Requirements:</div>
        <div className="grid grid-cols-2 gap-1">
          <div className={`flex items-center gap-1 ${strength.requirements.length ? 'text-green-600' : ''}`}>
            {strength.requirements.length ? '✓' : '○'} 8+ characters
          </div>
          <div className={`flex items-center gap-1 ${strength.requirements.uppercase ? 'text-green-600' : ''}`}>
            {strength.requirements.uppercase ? '✓' : '○'} Uppercase
          </div>
          <div className={`flex items-center gap-1 ${strength.requirements.lowercase ? 'text-green-600' : ''}`}>
            {strength.requirements.lowercase ? '✓' : '○'} Lowercase
          </div>
          <div className={`flex items-center gap-1 ${strength.requirements.number ? 'text-green-600' : ''}`}>
            {strength.requirements.number ? '✓' : '○'} Number
          </div>
          <div className={`flex items-center gap-1 ${strength.requirements.special ? 'text-green-600' : ''}`}>
            {strength.requirements.special ? '✓' : '○'} Special char
          </div>
        </div>
      </div>
    </div>
  );
}
