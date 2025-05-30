'use client';

import Image from 'next/image';
import { useState } from 'react';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export default function Logo({ size = 'md', showText = true, className = '' }: LogoProps) {
  const [imageError, setImageError] = useState(false);
  
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8', 
    lg: 'w-12 h-12'
  };

  const textSizeClasses = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl'
  };

  const sizeConfig = {
    container: sizeClasses[size],
    image: sizeClasses[size],
    text: textSizeClasses[size]
  };

  return (
    <div className={`flex items-center ${className}`}>
      <div className={`${sizeConfig.container} relative flex-shrink-0`}>
        {!imageError ? (
          <Image 
            src="/favicon-32x32.png" 
            className={`${sizeConfig.image} rounded-lg`}
            alt="ShiftIQ"
            width={32} 
            height={32}
            priority={size === 'lg'}
            onError={() => setImageError(true)}
          />
        ) : (
          // Fallback to text-based logo if image fails
          <div className={`${sizeConfig.container} bg-indigo-600 rounded-lg flex items-center justify-center`}>
            <span className="text-white font-bold text-sm">S</span>
          </div>
        )}
      </div>
      {showText && (
        <span className={`${sizeConfig.text} font-semibold text-gray-900 ml-3`}>
          ShiftIQ
        </span>
      )}
    </div>
  );
} 