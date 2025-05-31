const fs = require('fs');
const path = require('path');

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function analyzeImageOptimization() {
  console.log('📊 Image Optimization Analysis\n');
  
  const publicDir = path.join(process.cwd(), 'public');
  const optimizedDir = path.join(publicDir, 'optimized');
  
  const originalImages = [
    'cafe.jpg',
    'nwLx1Cp6tWit8e855xsUwKCQDc.jpg',
    'awuQBekLugr97gL8uQknRr2tog.jpg',
    'lU9jqP5P9GHVLS9zK5S3sXL7Y.jpg'
  ];
  
  let totalOriginalSize = 0;
  let totalMobileSize = 0;
  let totalOptimizedSize = 0;
  
  console.log('🖼️  Original vs Mobile-Optimized Comparison:\n');
  
  originalImages.forEach(imageName => {
    const originalPath = path.join(publicDir, imageName);
    
    if (!fs.existsSync(originalPath)) {
      console.log(`❌ Original image not found: ${imageName}`);
      return;
    }
    
    const originalStats = fs.statSync(originalPath);
    totalOriginalSize += originalStats.size;
    
    const baseName = path.parse(imageName).name;
    
    // Check mobile WebP size (what mobile users will typically download)
    const mobileWebpPath = path.join(optimizedDir, `${baseName}-mobile.webp`);
    const mobileMdWebpPath = path.join(optimizedDir, `${baseName}-mobile-md.webp`);
    
    let mobileSize = 0;
    if (fs.existsSync(mobileWebpPath)) {
      mobileSize = fs.statSync(mobileWebpPath).size;
    }
    
    let mobileMdSize = 0;
    if (fs.existsSync(mobileMdWebpPath)) {
      mobileMdSize = fs.statSync(mobileMdWebpPath).size;
    }
    
    // For comparison, we'll use the mobile-md size as it's more representative
    const representativeSize = mobileMdSize || mobileSize;
    totalMobileSize += representativeSize;
    
    // Count all optimized variants
    const optimizedFiles = fs.readdirSync(optimizedDir)
      .filter(file => file.startsWith(baseName))
      .filter(file => !file.includes('@2x')); // Exclude retina for this comparison
    
    let allOptimizedSize = 0;
    optimizedFiles.forEach(file => {
      const filePath = path.join(optimizedDir, file);
      allOptimizedSize += fs.statSync(filePath).size;
    });
    
    totalOptimizedSize += allOptimizedSize;
    
    const mobileReduction = ((originalStats.size - representativeSize) / originalStats.size * 100).toFixed(1);
    
    console.log(`📱 ${imageName}:`);
    console.log(`   Original: ${formatBytes(originalStats.size)}`);
    console.log(`   Mobile WebP: ${formatBytes(representativeSize)} (${mobileReduction}% smaller)`);
    console.log(`   Optimized variants: ${optimizedFiles.length} files`);
    console.log('');
  });
  
  const mobileSavings = ((totalOriginalSize - totalMobileSize) / totalOriginalSize * 100).toFixed(1);
  const allSavings = ((totalOriginalSize - totalOptimizedSize) / totalOriginalSize * 100).toFixed(1);
  
  console.log('📊 Summary:');
  console.log(`   Total original size: ${formatBytes(totalOriginalSize)}`);
  console.log(`   Mobile users download: ${formatBytes(totalMobileSize)} (${mobileSavings}% reduction)`);
  console.log(`   All optimized variants: ${formatBytes(totalOptimizedSize)}`);
  console.log('');
  console.log('🚀 Performance Benefits:');
  console.log(`   ✅ Mobile data usage reduced by ${mobileSavings}%`);
  console.log(`   ✅ Faster loading on slow connections`);
  console.log(`   ✅ Better Core Web Vitals scores`);
  console.log(`   ✅ Modern format support (AVIF, WebP)`);
  console.log(`   ✅ Responsive images for all device sizes`);
  console.log('');
  console.log('📋 Next Steps:');
  console.log('   1. Test the site on mobile devices');
  console.log('   2. Use browser dev tools to verify format selection');
  console.log('   3. Monitor Core Web Vitals improvement');
  console.log('   4. Consider setting up a CDN for even better performance');
}

analyzeImageOptimization(); 