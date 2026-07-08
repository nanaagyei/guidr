'use client';

import { InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface RadioOption {
  value: string;
  label: string;
  description?: string;
}

interface RadioGroupProps {
  label?: string;
  options: RadioOption[];
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  className?: string;
  name: string;
}

export function RadioGroup({
  label,
  options,
  value,
  onChange,
  error,
  className,
  name,
}: RadioGroupProps) {
  return (
    <div className={cn('w-full', className)}>
      {label && (
        <label className="block text-sm font-medium text-text mb-3">
          {label}
        </label>
      )}
      <div className="space-y-3">
        {options.map((option) => (
          <label
            key={option.value}
            className={cn(
              'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
              'hover:bg-gray-50',
              value === option.value
                ? 'border-primary bg-primary/5'
                : 'border-border'
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(e) => onChange?.(e.target.value)}
              className="mt-1 h-4 w-4 text-primary focus:ring-primary border-gray-300"
            />
            <div className="flex-1">
              <div className="text-sm font-medium text-text">{option.label}</div>
              {option.description && (
                <div className="text-xs text-gray-500 mt-0.5">{option.description}</div>
              )}
            </div>
          </label>
        ))}
      </div>
      {error && (
        <p className="mt-1.5 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
