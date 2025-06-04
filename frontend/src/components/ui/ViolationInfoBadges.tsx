import React from 'react';

interface ViolationInfoBadgesProps {
  violationCount: number;
  infoCount: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'badges' | 'text' | 'compact';
  showZeroCounts?: boolean;
  className?: string;
}

export const ViolationInfoBadges: React.FC<ViolationInfoBadgesProps> = ({
  violationCount,
  infoCount,
  size = 'md',
  variant = 'badges',
  showZeroCounts = false,
  className = ''
}) => {
  // Size configurations
  const sizeConfig = {
    sm: {
      badge: 'px-1.5 py-0.5 text-xs',
      dot: 'w-1 h-1',
      text: 'text-xs'
    },
    md: {
      badge: 'px-2 py-1 text-xs',
      dot: 'w-1.5 h-1.5',
      text: 'text-sm'
    },
    lg: {
      badge: 'px-2.5 py-1 text-sm',
      dot: 'w-2 h-2',
      text: 'text-base'
    }
  };

  const config = sizeConfig[size];

  // Text variant - for filter panels and headers
  if (variant === 'text') {
    const parts = [];
    if (violationCount > 0 || showZeroCounts) {
      parts.push(`${violationCount} violation${violationCount !== 1 ? 's' : ''}`);
    }
    if (infoCount > 0 || showZeroCounts) {
      parts.push(`${infoCount} info`);
    }
    
    if (parts.length === 0) return null;
    
    return (
      <span className={`${config.text} text-gray-600 ${className}`}>
        {parts.join(', ')}
      </span>
    );
  }

  // Compact variant - for tight spaces
  if (variant === 'compact') {
    if (violationCount === 0 && infoCount === 0 && !showZeroCounts) return null;
    
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {(violationCount > 0 || showZeroCounts) && (
          <span className={`inline-flex items-center gap-1 ${config.badge} bg-red-50 text-red-700 rounded font-medium border border-red-200`}>
            <div className={`${config.dot} bg-red-500 rounded-full`}></div>
            {violationCount}
          </span>
        )}
        {(infoCount > 0 || showZeroCounts) && (
          <span className={`inline-flex items-center gap-1 ${config.badge} bg-yellow-50 text-yellow-700 rounded font-medium border border-yellow-200`}>
            <div className={`${config.dot} bg-yellow-500 rounded-full`}></div>
            {infoCount}
          </span>
        )}
      </div>
    );
  }

  // Default badges variant - for accordion headers and main displays
  if (violationCount === 0 && infoCount === 0 && !showZeroCounts) return null;

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {(violationCount > 0 || showZeroCounts) && (
        <span className={`inline-flex items-center gap-1 ${config.badge} bg-red-100 text-red-800 rounded-full font-medium border border-red-200`}>
          <div className={`${config.dot} bg-red-500 rounded-full`}></div>
          {violationCount} violation{violationCount !== 1 ? 's' : ''}
        </span>
      )}
      {(infoCount > 0 || showZeroCounts) && (
        <span className={`inline-flex items-center gap-1 ${config.badge} bg-yellow-100 text-yellow-800 rounded-full font-medium border border-yellow-200`}>
          <div className={`${config.dot} bg-yellow-500 rounded-full`}></div>
          {infoCount} info
        </span>
      )}
    </div>
  );
};

export default ViolationInfoBadges; 