const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Define the sizes we want to generate
const imageSizes = {
  // Mobile sizes
  mobile: { width: 480, suffix: '-mobile' },
  mobileMd: { width: 768, suffix: '-mobile-md' },
  // Tablet sizes  
  tablet: { width: 1024, suffix: '-tablet' },
  // Desktop sizes
  desktop: { width: 1920, suffix: '-desktop' },
  // Retina versions
  mobile2x: { width: 960, suffix: '-mobile@2x' },
  tablet2x: { width: 2048, suffix: '-tablet@2x' }
};

// Quality settings for different formats
const qualitySettings = {
  webp: { quality: 85, effort: 6 },
  jpeg: { quality: 85, progressive: true },
  avif: { quality: 80, effort: 4 }
};

async function optimizeImage(inputPath, outputDir, filename) {
  console.log(`\n🖼️  Optimizing: ${filename}`);
  
  const baseName = path.parse(filename).name;
  const originalImage = sharp(inputPath);
  const metadata = await originalImage.metadata();
  
  console.log(`   Original: ${metadata.width}x${metadata.height} (${Math.round(metadata.size / 1024)}KB)`);
  
  // Create output directory if it doesn't exist
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const results = [];
  
  // Generate different sizes and formats
  for (const [sizeName, sizeConfig] of Object.entries(imageSizes)) {
    // Skip if the original is smaller than the target size
    if (metadata.width < sizeConfig.width) {
      console.log(`   ⏭️  Skipping ${sizeName} (${sizeConfig.width}px) - original is smaller`);
      continue;
    }
    
    const resizedImage = originalImage.resize(sizeConfig.width, null, {
      withoutEnlargement: true,
      fit: 'inside'
    });
    
    // Generate WebP (modern format, best compression)
    try {
      const webpPath = path.join(outputDir, `${baseName}${sizeConfig.suffix}.webp`);
      const webpStats = await resizedImage
        .webp(qualitySettings.webp)
        .toFile(webpPath);
      
      results.push({
        format: 'webp',
        size: sizeName,
        path: webpPath,
        width: webpStats.width,
        height: webpStats.height,
        fileSize: webpStats.size
      });
      
      console.log(`   ✅ WebP ${sizeName}: ${webpStats.width}x${webpStats.height} (${Math.round(webpStats.size / 1024)}KB)`);
    } catch (error) {
      console.log(`   ❌ Failed to create WebP ${sizeName}: ${error.message}`);
    }
    
    // Generate AVIF (next-gen format, even better compression)
    try {
      const avifPath = path.join(outputDir, `${baseName}${sizeConfig.suffix}.avif`);
      const avifStats = await resizedImage
        .avif(qualitySettings.avif)
        .toFile(avifPath);
      
      results.push({
        format: 'avif',
        size: sizeName,
        path: avifPath,
        width: avifStats.width,
        height: avifStats.height,
        fileSize: avifStats.size
      });
      
      console.log(`   ✅ AVIF ${sizeName}: ${avifStats.width}x${avifStats.height} (${Math.round(avifStats.size / 1024)}KB)`);
    } catch (error) {
      console.log(`   ❌ Failed to create AVIF ${sizeName}: ${error.message}`);
    }
    
    // Generate JPEG fallback for mobile and tablet only
    if (['mobile', 'mobileMd', 'tablet'].includes(sizeName)) {
      try {
        const jpegPath = path.join(outputDir, `${baseName}${sizeConfig.suffix}.jpg`);
        const jpegStats = await resizedImage
          .jpeg(qualitySettings.jpeg)
          .toFile(jpegPath);
        
        results.push({
          format: 'jpeg',
          size: sizeName,
          path: jpegPath,
          width: jpegStats.width,
          height: jpegStats.height,
          fileSize: jpegStats.size
        });
        
        console.log(`   ✅ JPEG ${sizeName}: ${jpegStats.width}x${jpegStats.height} (${Math.round(jpegStats.size / 1024)}KB)`);
      } catch (error) {
        console.log(`   ❌ Failed to create JPEG ${sizeName}: ${error.message}`);
      }
    }
  }
  
  return results;
}

async function generateResponsiveImageHelper(imageName, results) {
  const baseName = path.parse(imageName).name;
  
  // Group results by format
  const byFormat = results.reduce((acc, result) => {
    if (!acc[result.format]) acc[result.format] = [];
    acc[result.format].push(result);
    return acc;
  }, {});
  
  // Generate srcSet strings for each format
  const srcSets = {};
  
  Object.entries(byFormat).forEach(([format, images]) => {
    const srcSetEntries = images
      .sort((a, b) => a.width - b.width)
      .map(img => {
        const relativePath = path.relative('public', img.path);
        return `/${relativePath} ${img.width}w`;
      });
    
    srcSets[format] = srcSetEntries.join(', ');
  });
  
  // Generate React component code
  const componentCode = `
// Responsive image component for ${imageName}
export const ${baseName}ResponsiveImage = ({ 
  alt, 
  className = "",
  sizes = "(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw",
  priority = false 
}) => {
  return (
    <picture>
      ${srcSets.avif ? `<source srcSet="${srcSets.avif}" type="image/avif" sizes={sizes} />` : ''}
      ${srcSets.webp ? `<source srcSet="${srcSets.webp}" type="image/webp" sizes={sizes} />` : ''}
      <img
        src="${srcSets.jpeg ? `/${path.relative('public', byFormat.jpeg[0].path)}` : `/${imageName}`}"
        ${srcSets.jpeg ? `srcSet="${srcSets.jpeg}"` : ''}
        alt={alt}
        className={className}
        loading={priority ? "eager" : "lazy"}
        sizes={sizes}
      />
    </picture>
  );
};`;

  return componentCode;
}

async function main() {
  console.log('📱 Starting mobile image optimization...\n');
  
  const publicDir = path.join(process.cwd(), 'public');
  const optimizedDir = path.join(publicDir, 'optimized');
  
  // List of images to optimize
  const imagesToOptimize = [
    'cafe.jpg',
    'nwLx1Cp6tWit8e855xsUwKCQDc.jpg',
    'awuQBekLugr97gL8uQknRr2tog.jpg',
    'lU9jqP5P9GHVLS9zK5S3sXL7Y.jpg'
  ];
  
  const allResults = {};
  
  for (const imageName of imagesToOptimize) {
    const inputPath = path.join(publicDir, imageName);
    
    if (!fs.existsSync(inputPath)) {
      console.log(`⚠️  Image not found: ${imageName}`);
      continue;
    }
    
    try {
      const results = await optimizeImage(inputPath, optimizedDir, imageName);
      allResults[imageName] = results;
    } catch (error) {
      console.log(`❌ Failed to optimize ${imageName}: ${error.message}`);
    }
  }
  
  // Generate helper components file
  console.log('\n📝 Generating responsive image components...');
  
  let componentsCode = `// Auto-generated responsive image components
// Generated on ${new Date().toISOString()}

import React from 'react';

`;

  for (const [imageName, results] of Object.entries(allResults)) {
    if (results.length > 0) {
      componentsCode += await generateResponsiveImageHelper(imageName, results);
      componentsCode += '\n';
    }
  }
  
  const componentsPath = path.join(process.cwd(), 'src', 'components', 'ResponsiveImages.tsx');
  fs.writeFileSync(componentsPath, componentsCode);
  
  console.log(`✅ Generated responsive image components: ${componentsPath}`);
  
  // Generate usage documentation
  const docsContent = `# Mobile Optimized Images

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
\`\`\`tsx
import { cafeResponsiveImage } from '@/components/ResponsiveImages';

<cafeResponsiveImage 
  alt="Professional cafe environment"
  className="w-full h-full object-cover"
  priority={true}
/>
\`\`\`

### Option 2: Use Next.js Image component with srcSet
\`\`\`tsx
import Image from 'next/image';

<Image
  src="/optimized/cafe-mobile.webp"
  alt="Professional cafe environment"
  width={480}
  height={320}
  sizes="(max-width: 768px) 100vw, 50vw"
  priority
/>
\`\`\`

### Option 3: Manual picture element for maximum control
\`\`\`tsx
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
\`\`\`

## Performance Benefits:
- Up to 80% smaller file sizes
- Faster loading on mobile devices
- Better Core Web Vitals scores
- Automatic format selection based on browser support
`;

  fs.writeFileSync(path.join(optimizedDir, 'README.md'), docsContent);
  
  console.log('\n🎉 Image optimization complete!');
  console.log('\n📊 Summary:');
  
  let totalOriginalSize = 0;
  let totalOptimizedSize = 0;
  
  for (const [imageName, results] of Object.entries(allResults)) {
    const originalPath = path.join(publicDir, imageName);
    const originalStats = fs.statSync(originalPath);
    totalOriginalSize += originalStats.size;
    
    const optimizedSize = results.reduce((sum, result) => sum + result.fileSize, 0);
    totalOptimizedSize += optimizedSize;
    
    console.log(`   ${imageName}: ${Math.round(originalStats.size / 1024)}KB → ${Math.round(optimizedSize / 1024)}KB (${results.length} variants)`);
  }
  
  const savings = ((totalOriginalSize - totalOptimizedSize) / totalOriginalSize * 100).toFixed(1);
  console.log(`\n💾 Total savings: ${Math.round((totalOriginalSize - totalOptimizedSize) / 1024)}KB (${savings}%)`);
  console.log('\n📖 See public/optimized/README.md for usage instructions');
}

// Run the optimization
main().catch(console.error); 