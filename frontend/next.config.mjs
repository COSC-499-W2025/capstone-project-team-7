/** @type {import('next').NextConfig} */
const nextConfig = {
  // Only use static export for production builds (Electron)
  // Dev server needs dynamic rendering for auth routes
  ...(process.env.NODE_ENV === 'production' && { output: 'export' }),
  // Electron loads via file:// where absolute paths break — use relative paths
  ...(process.env.ELECTRON_BUILD === 'true' && { assetPrefix: './' }),
  eslint: {
    ignoreDuringBuilds: true,
  },
  experimental: {
    typedRoutes: true
  }
};

export default nextConfig;
