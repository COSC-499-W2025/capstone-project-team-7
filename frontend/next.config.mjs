/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export only for Electron desktop builds.
  // Web deployments (Vercel, Railway) use standard Next.js server mode.
  // Set BUILD_TARGET=electron when building for desktop.
  ...(process.env.BUILD_TARGET === 'electron' && { output: 'export' }),
  experimental: {
    typedRoutes: true
  }
};

export default nextConfig;
