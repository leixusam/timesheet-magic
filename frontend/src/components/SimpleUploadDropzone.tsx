'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { uploadAndRedirect, UploadProgress } from '@/utils/uploadRedirect';
import analytics from '@/utils/analytics';

interface SimpleUploadDropzoneProps {
  className?: string;
}

export default function SimpleUploadDropzone({ className = '' }: SimpleUploadDropzoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropzoneRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    
    // Task 5.3: Track upload start conversion event
    analytics.trackUploadStart({
      name: file.name,
      size: file.size,
      type: file.type
    });
    
    // Reset states
    setUploading(true);
    setError(null);
    setProgress(null);

    const uploadStartTime = Date.now();

    try {
      const result = await uploadAndRedirect({
        file,
        router,
        onProgress: (progressUpdate) => {
          setProgress(progressUpdate);
        },
        onError: (errorMessage) => {
          setError(errorMessage);
          setUploading(false);
          
          // Track upload error
          analytics.trackError({
            message: errorMessage,
            context: 'file_upload',
          });
        }
      });
      
      // Task 5.3: Track upload success conversion event if result is available
      if (result && result.success && result.requestId) {
        const processingTime = Date.now() - uploadStartTime;
        analytics.trackUploadSuccess({
          requestId: result.requestId,
          fileName: file.name,
          processingTime: processingTime
        });
      }
      
      // Note: If successful, the component will unmount due to navigation
      // so we don't need to reset uploading state here
      
    } catch (error) {
      console.error('Upload error:', error);
      setUploading(false);
      const errorMessage = error instanceof Error ? error.message : 'Upload failed. Please try again.';
      setError(errorMessage);
      
      // Track upload error
      analytics.trackError({
        message: errorMessage,
        context: 'file_upload_catch',
        stack: error instanceof Error ? error.stack : undefined
      });
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (uploading) return;
    
    handleFiles(e.dataTransfer.files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (uploading) return;
    handleFiles(e.target.files);
  };

  const onButtonClick = () => {
    if (uploading) return;
    inputRef.current?.click();
  };

  // Handle keyboard events for dropzone
  const handleDropzoneKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onButtonClick();
    }
  };

  const handleDropzoneFocus = () => {
    setFocused(true);
  };

  const handleDropzoneBlur = () => {
    setFocused(false);
  };

  // Reset error when user tries again
  const handleRetry = () => {
    setError(null);
    onButtonClick();
  };

  // Show error state
  if (error && !uploading) {
    return (
      <div className={`${className}`}>
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-red-900 mb-2">Upload Failed</h3>
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={handleRetry}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Show upload progress
  if (uploading) {
    const progressPercent = progress?.progress || 0;
    const progressMessage = progress?.message || 'Preparing upload...';
    const progressStage = progress?.stage || 'validating';

    // Dynamic progress bar color based on stage
    const getProgressColor = () => {
      switch (progressStage) {
        case 'validating': return 'bg-yellow-500';
        case 'uploading': return 'bg-blue-500';
        case 'processing': return 'bg-indigo-500';
        case 'complete': return 'bg-green-500';
        case 'error': return 'bg-red-500';
        default: return 'bg-blue-500';
      }
    };

    return (
      <div className={`${className}`}>
        <div className="text-center py-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-indigo-100 rounded-full flex items-center justify-center">
            {progressStage === 'complete' ? (
              <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {progressStage === 'complete' ? 'Upload Complete!' : 'Uploading & Starting Analysis'}
          </h3>
          <p className="text-gray-600 mb-4">{progressMessage}</p>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-500">{progressPercent}% complete</p>
        </div>
      </div>
    );
  }

  // Show upload dropzone
  return (
    <div className={`${className}`}>
      {/* Upload Section Title */}
      <div className="text-center mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Upload your timesheet
        </h3>
        <p className="text-sm text-gray-500">
          CSV, Excel, PDF, or images
        </p>
      </div>

      <div
        ref={dropzoneRef}
        className={`relative border-2 border-dashed rounded-xl p-8 transition-all cursor-pointer ${
          dragActive 
            ? 'border-black bg-gray-50' 
            : focused
            ? 'border-black bg-gray-50'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onKeyDown={handleDropzoneKeyDown}
        onFocus={handleDropzoneFocus}
        onBlur={handleDropzoneBlur}
        onClick={onButtonClick}
        tabIndex={0}
        role="button"
        aria-label="Upload timesheet file"
        aria-describedby="upload-description"
      >
        <input
          ref={inputRef}
          type="file"
          multiple={false}
          className="absolute inset-0 w-full h-full opacity-0 pointer-events-none"
          onChange={handleChange}
          accept=".csv,.xlsx,.xls,.pdf,.jpg,.jpeg,.png,.gif,.webp"
          tabIndex={-1}
          aria-hidden="true"
        />
        
        <div className="text-center">
          {/* Upload Icon */}
          <div className="mb-4">
            <svg className="w-12 h-12 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          
          <div className="mb-4">
            <span className="inline-flex items-center justify-center w-full py-3 text-base font-medium text-black rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors">
              Choose file
            </span>
          </div>
          <p id="upload-description" className="text-sm text-gray-500">
            Drag and drop or click to upload
          </p>
        </div>
      </div>
    </div>
  );
} 