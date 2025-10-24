/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { dev, isServer }) => {
    // Add support for .tif and .tiff files
    config.module.rules.push({
      test: /\.(tif|tiff)$/,
      type: 'asset/resource',
    });
    
    // Suppress source map warnings
    if (dev) {
      config.devtool = false;
    }
    
    return config;
  },
  // Suppress the installHook.js.map 404 warnings
  productionBrowserSourceMaps: false,
  // Disable React DevTools source maps
  reactStrictMode: true,
};

export default nextConfig;
