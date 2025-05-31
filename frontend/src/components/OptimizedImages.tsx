import React from 'react';

interface ResponsiveImageProps {
  alt: string;
  className?: string;
  sizes?: string;
  priority?: boolean;
}

// Hero background image component
export const CafeHeroImage: React.FC<ResponsiveImageProps> = ({ 
  alt, 
  className = "",
  sizes = "(max-width: 768px) 100vw, (max-width: 1024px) 100vw, 100vw",
  priority = false 
}) => {
  return (
    <picture>
      <source 
        srcSet="/optimized/cafe-mobile.avif 480w, /optimized/cafe-mobile-md.avif 768w, /optimized/cafe-mobile@2x.avif 960w, /optimized/cafe-tablet.avif 1024w" 
        type="image/avif" 
        sizes={sizes} 
      />
      <source 
        srcSet="/optimized/cafe-mobile.webp 480w, /optimized/cafe-mobile-md.webp 768w, /optimized/cafe-mobile@2x.webp 960w, /optimized/cafe-tablet.webp 1024w" 
        type="image/webp" 
        sizes={sizes} 
      />
      <img
        src="/optimized/cafe-mobile.jpg"
        srcSet="/optimized/cafe-mobile.jpg 480w, /optimized/cafe-mobile-md.jpg 768w, /optimized/cafe-tablet.jpg 1024w"
        alt={alt}
        className={className}
        loading={priority ? "eager" : "lazy"}
        sizes={sizes}
      />
    </picture>
  );
};

// Kitchen staff image component
export const KitchenStaffImage: React.FC<ResponsiveImageProps> = ({ 
  alt, 
  className = "",
  sizes = "(max-width: 768px) 80vw, (max-width: 1024px) 50vw, 33vw",
  priority = false 
}) => {
  return (
    <picture>
      <source 
        srcSet="/optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile.avif 480w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile-md.avif 768w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile@2x.avif 960w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-tablet.avif 1024w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-desktop.avif 1920w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-tablet@2x.avif 2048w" 
        type="image/avif" 
        sizes={sizes} 
      />
      <source 
        srcSet="/optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile.webp 480w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile-md.webp 768w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile@2x.webp 960w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-tablet.webp 1024w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-desktop.webp 1920w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-tablet@2x.webp 2048w" 
        type="image/webp" 
        sizes={sizes} 
      />
      <img
        src="/optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile.jpg"
        srcSet="/optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile.jpg 480w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-mobile-md.jpg 768w, /optimized/nwLx1Cp6tWit8e855xsUwKCQDc-tablet.jpg 1024w"
        alt={alt}
        className={className}
        loading={priority ? "eager" : "lazy"}
        sizes={sizes}
      />
    </picture>
  );
};

// Employee timesheet image component
export const EmployeeTimesheetImage: React.FC<ResponsiveImageProps> = ({ 
  alt, 
  className = "",
  sizes = "(max-width: 768px) 80vw, (max-width: 1024px) 50vw, 33vw",
  priority = false 
}) => {
  return (
    <picture>
      <source 
        srcSet="/optimized/awuQBekLugr97gL8uQknRr2tog-mobile.avif 480w, /optimized/awuQBekLugr97gL8uQknRr2tog-mobile-md.avif 768w, /optimized/awuQBekLugr97gL8uQknRr2tog-mobile@2x.avif 960w, /optimized/awuQBekLugr97gL8uQknRr2tog-tablet.avif 1024w, /optimized/awuQBekLugr97gL8uQknRr2tog-desktop.avif 1920w, /optimized/awuQBekLugr97gL8uQknRr2tog-tablet@2x.avif 2048w" 
        type="image/avif" 
        sizes={sizes} 
      />
      <source 
        srcSet="/optimized/awuQBekLugr97gL8uQknRr2tog-mobile.webp 480w, /optimized/awuQBekLugr97gL8uQknRr2tog-mobile-md.webp 768w, /optimized/awuQBekLugr97gL8uQknRr2tog-mobile@2x.webp 960w, /optimized/awuQBekLugr97gL8uQknRr2tog-tablet.webp 1024w, /optimized/awuQBekLugr97gL8uQknRr2tog-desktop.webp 1920w, /optimized/awuQBekLugr97gL8uQknRr2tog-tablet@2x.webp 2048w" 
        type="image/webp" 
        sizes={sizes} 
      />
      <img
        src="/optimized/awuQBekLugr97gL8uQknRr2tog-mobile.jpg"
        srcSet="/optimized/awuQBekLugr97gL8uQknRr2tog-mobile.jpg 480w, /optimized/awuQBekLugr97gL8uQknRr2tog-mobile-md.jpg 768w, /optimized/awuQBekLugr97gL8uQknRr2tog-tablet.jpg 1024w"
        alt={alt}
        className={className}
        loading={priority ? "eager" : "lazy"}
        sizes={sizes}
      />
    </picture>
  );
};

// Compliance checklist image component
export const ComplianceChecklistImage: React.FC<ResponsiveImageProps> = ({ 
  alt, 
  className = "",
  sizes = "(max-width: 768px) 80vw, (max-width: 1024px) 50vw, 33vw",
  priority = false 
}) => {
  return (
    <picture>
      <source 
        srcSet="/optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile.avif 480w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile-md.avif 768w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile@2x.avif 960w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-tablet.avif 1024w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-desktop.avif 1920w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-tablet@2x.avif 2048w" 
        type="image/avif" 
        sizes={sizes} 
      />
      <source 
        srcSet="/optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile.webp 480w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile-md.webp 768w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile@2x.webp 960w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-tablet.webp 1024w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-desktop.webp 1920w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-tablet@2x.webp 2048w" 
        type="image/webp" 
        sizes={sizes} 
      />
      <img
        src="/optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile.jpg"
        srcSet="/optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile.jpg 480w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-mobile-md.jpg 768w, /optimized/lU9jqP5P9GHVLS9zK5S3sXL7Y-tablet.jpg 1024w"
        alt={alt}
        className={className}
        loading={priority ? "eager" : "lazy"}
        sizes={sizes}
      />
    </picture>
  );
}; 