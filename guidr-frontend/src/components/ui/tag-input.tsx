'use client';

import { ClipboardEvent, KeyboardEvent, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TagInputProps {
  value: string[];
  onChange: (values: string[]) => void;
  label?: string;
  placeholder?: string;
  helperText?: string;
  error?: string;
  className?: string;
  disabled?: boolean;
  /** Maximum number of tags allowed (default: unlimited) */
  maxTags?: number;
  /** Maximum character length per tag (default: 100) */
  maxTagLength?: number;
}

/**
 * TagInput — a chip-style multi-value text input.
 *
 * Tags are created by pressing comma or Enter.
 * Spaces within a tag are preserved (e.g. "Machine Learning" is one tag).
 * Backspace on an empty input removes the last tag.
 * Paste support: comma-separated text is split into individual tags.
 */
export function TagInput({
  value,
  onChange,
  label,
  placeholder,
  helperText,
  error,
  className,
  disabled = false,
  maxTags,
  maxTagLength = 100,
}: TagInputProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const addTag = (raw: string) => {
    const tag = raw.trim().slice(0, maxTagLength);
    if (!tag) return;
    if (maxTags && value.length >= maxTags) return;
    // Avoid duplicates (case-insensitive)
    if (value.some((v) => v.toLowerCase() === tag.toLowerCase())) return;
    onChange([...value, tag]);
  };

  const addMultipleTags = (raw: string) => {
    const candidates = raw.split(',');
    let current = [...value];
    for (const candidate of candidates) {
      const tag = candidate.trim().slice(0, maxTagLength);
      if (!tag) continue;
      if (maxTags && current.length >= maxTags) break;
      if (current.some((v) => v.toLowerCase() === tag.toLowerCase())) continue;
      current = [...current, tag];
    }
    if (current.length !== value.length) {
      onChange(current);
    }
  };

  const removeTag = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === ',' || e.key === 'Enter') {
      e.preventDefault();
      addTag(inputValue);
      setInputValue('');
    } else if (e.key === 'Backspace' && inputValue === '' && value.length > 0) {
      removeTag(value.length - 1);
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    const text = e.clipboardData.getData('text');
    if (text.includes(',')) {
      e.preventDefault();
      addMultipleTags(text);
      setInputValue('');
    }
  };

  const handleBlur = () => {
    // Create tag on blur if there's pending text
    if (inputValue.trim()) {
      addTag(inputValue);
      setInputValue('');
    }
  };

  const atLimit = maxTags !== undefined && value.length >= maxTags;

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <label className="block text-sm font-medium text-text mb-1.5">
          {label}
        </label>
      )}

      {/* Tag container — click anywhere to focus the hidden input */}
      <div
        aria-label={label || 'Tag input'}
        className={cn(
          'min-h-[42px] w-full px-3 py-2 rounded-lg border transition-colors',
          'bg-card flex flex-wrap gap-1.5 items-center cursor-text',
          'focus-within:ring-2 focus-within:ring-primary focus-within:border-transparent',
          error
            ? 'border-red-300 focus-within:ring-red-500'
            : 'border-border hover:border-primary/50',
          disabled && 'bg-gray-100 cursor-not-allowed',
        )}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Rendered tags */}
        {value.map((tag, index) => (
          <span
            key={index}
            className={cn(
              'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-medium',
              'bg-primary/10 text-primary border border-primary/20',
            )}
          >
            {tag}
            {!disabled && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeTag(index);
                }}
                className="text-primary/60 hover:text-primary transition-colors ml-0.5"
                aria-label={`Remove ${tag}`}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        ))}

        {/* Text input — hidden when at limit */}
        {!atLimit && !disabled && (
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            onBlur={handleBlur}
            placeholder={value.length === 0 ? placeholder : 'Add more\u2026'}
            className={cn(
              'flex-1 min-w-[120px] bg-transparent outline-none text-sm text-text',
              'placeholder:text-gray-400',
            )}
            disabled={disabled}
          />
        )}
      </div>

      {error && <p className="mt-1.5 text-sm text-red-600">{error}</p>}
      {helperText && !error && (
        <p className="mt-1.5 text-sm text-gray-500">{helperText}</p>
      )}
      {maxTags && value.length > 0 && (
        <p className="mt-1 text-xs text-gray-400">
          {value.length}/{maxTags}
        </p>
      )}
    </div>
  );
}
