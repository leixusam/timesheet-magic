# Mobile Optimized Images

This directory contains mobile-optimized versions of your images in multiple formats and sizes.

## Generated Sizes:
- **Mobile**: 480px wide (for phones)
- **Mobile MD**: 768px wide (for large phones/small tablets)  
- **Tablet**: 1024px wide (for tablets)
- **Desktop**: 1920px wide (for desktop)
- **Retina versions**: @2x versions for high-DPI displays

## Formats Generated:
- **AVIF**: Next-generation format with best compression
- **WebP**: Modern format with excellent compression
- **JPEG**: Fallback format for older browsers

## Usage in Next.js:

### Option 1: Use the generated responsive components
```tsx
import { cafeResponsiveImage } from '@/components/ResponsiveImages';

<cafeResponsiveImage 
  alt="Professional cafe environment"
  className="w-full h-full object-cover"
  priority={true}
/>
```

### Option 2: Use Next.js Image component with srcSet
```tsx
import Image from 'next/image';

<Image
  src="/optimized/cafe-mobile.webp"
  alt="Professional cafe environment"
  width={480}
  height={320}
  sizes="(max-width: 768px) 100vw, 50vw"
  priority
/>
```

### Option 3: Manual picture element for maximum control
```tsx
<picture>
  <source 
    srcSet="/optimized/cafe-mobile.avif 480w, /optimized/cafe-tablet.avif 1024w"
    type="image/avif"
    sizes="(max-width: 768px) 100vw, 50vw"
  />
  <source 
    srcSet="/optimized/cafe-mobile.webp 480w, /optimized/cafe-tablet.webp 1024w"
    type="image/webp"
    sizes="(max-width: 768px) 100vw, 50vw"
  />
  <img 
    src="/optimized/cafe-mobile.jpg"
    alt="Professional cafe environment"
    loading="lazy"
  />
</picture>
```

## Performance Benefits:
- Up to 80% smaller file sizes
- Faster loading on mobile devices
- Better Core Web Vitals scores
- Automatic format selection based on browser support
