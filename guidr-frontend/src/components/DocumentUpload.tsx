'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, File, X, CheckCircle2, AlertCircle } from 'lucide-react';

interface DocumentUploadProps {
  onUpload: (file: File, documentType: string) => Promise<void>;
  onClose: () => void;
  uploading?: boolean;
  error?: string;
}

export default function DocumentUpload({ onUpload, onClose, uploading = false, error }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('transcript');
  const [isDragging, setIsDragging] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile && isFileValid(droppedFile)) {
      setFile(droppedFile);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isFileValid(selectedFile)) {
      setFile(selectedFile);
    }
  }, []);

  const isFileValid = (file: File): boolean => {
    const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    const validExtensions = ['.pdf', '.doc', '.docx', '.txt'];
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    return validTypes.includes(file.type) || validExtensions.includes(extension);
  };

  const handleSubmit = async () => {
    if (file) {
      await onUpload(file, documentType);
      setFile(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-card rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        >
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-text">Upload Document</h2>
              <button
                onClick={onClose}
                disabled={uploading}
                className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
              >
                <X className="h-5 w-5 text-textSecondary" />
              </button>
            </div>

            <div className="space-y-6">
              {/* Document Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Document Type *
                </label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  disabled={uploading}
                  className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white disabled:opacity-50"
                >
                  <option value="transcript">Transcript</option>
                  <option value="resume">Resume</option>
                  <option value="essay">Essay</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Drag and Drop Area */}
              <div
                onDragEnter={handleDragEnter}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                  isDragging
                    ? 'border-primary bg-primary/10 scale-105'
                    : 'border-border bg-muted hover:border-primary/50'
                }`}
              >
                <input
                  type="file"
                  id="file-input"
                  onChange={handleFileSelect}
                  accept=".pdf,.doc,.docx,.txt"
                  disabled={uploading}
                  className="hidden"
                />

                <AnimatePresence mode="wait">
                  {!file ? (
                    <motion.div
                      key="upload-prompt"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="space-y-4"
                    >
                      <motion.div
                        animate={isDragging ? { scale: 1.1, rotate: 5 } : { scale: 1, rotate: 0 }}
                        transition={{ type: 'spring', stiffness: 300 }}
                        className="flex justify-center"
                      >
                        <Upload className="h-12 w-12 text-textSecondary" />
                      </motion.div>
                      <div>
                        <p className="text-lg font-medium text-text mb-2">
                          {isDragging ? 'Drop your file here' : 'Drag & drop your file here'}
                        </p>
                        <p className="text-sm text-gray-600 mb-4">
                          or click to browse
                        </p>
                        <label
                          htmlFor="file-input"
                          className="inline-block px-6 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition cursor-pointer disabled:opacity-50"
                        >
                          Select File
                        </label>
                      </div>
                      <p className="text-xs text-gray-500">
                        Supported formats: PDF, DOC, DOCX, TXT (Max 10MB)
                      </p>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="file-preview"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      className="space-y-4"
                    >
                      <div className="flex items-center justify-center">
                        <div className="relative">
                          <div className="h-16 w-16 bg-primary/10 rounded-xl flex items-center justify-center">
                            <File className="h-8 w-8 text-primary" />
                          </div>
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="absolute -top-1 -right-1"
                          >
                            <CheckCircle2 className="h-6 w-6 text-green-500 bg-white rounded-full" />
                          </motion.div>
                        </div>
                      </div>
                      <div>
                        <p className="font-semibold text-text">{file.name}</p>
                        <p className="text-sm text-gray-600">{formatFileSize(file.size)}</p>
                      </div>
                      <button
                        onClick={() => setFile(null)}
                        disabled={uploading}
                        className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                      >
                        Remove file
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Error Display */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 p-3 bg-red-100 border border-red-300 rounded-lg text-red-700"
                >
                  <AlertCircle className="h-5 w-5 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                </motion.div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4">
                <button
                  onClick={handleSubmit}
                  disabled={!file || uploading}
                  className="flex-1 px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="h-5 w-5 border-2 border-white border-t-transparent rounded-full"
                      />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-5 w-5" />
                      Upload Document
                    </>
                  )}
                </button>
                <button
                  onClick={onClose}
                  disabled={uploading}
                  className="px-6 py-3 bg-gray-200 text-gray-700 font-semibold rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

