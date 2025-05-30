'use client';

import Image from 'next/image';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export default function Logo({ size = 'md', showText = true, className = '' }: LogoProps) {
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
        {/* ShiftIQ Icon - High Resolution */}
        <Image 
          src="/icon-high-res.png" 
          className={`${sizeConfig.image} rounded-lg`}
          alt="ShiftIQ"
          width={256} 
          height={256}
          priority={size === 'lg'}
        />
      </div>
      {showText && (
        <span className={`${sizeConfig.text} font-semibold text-gray-900 ml-3`}>
          ShiftIQ
        </span>
      )}
    </div>
  );
} 