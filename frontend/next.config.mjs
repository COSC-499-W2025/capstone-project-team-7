/** @type {import('next').NextConfig} */
const nextConfig = {
  // Only use static export for production builds (Electron)
  // Dev server needs dynamic rendering for auth routes
  ...(process.env.NODE_ENV === 'production' && { output: 'export' }),
  eslint: {
    ignoreDuringBuilds: true,
  },
  experimental: {
    typedRoutes: true
  }
};

export default nextConfig;
