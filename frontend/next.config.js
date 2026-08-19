/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  webpack: (config, { dev }) => {
    if (dev) {
      // Disable Webpack disk caching during development to prevent PackFileCacheStrategy chunk corruption & HMR 500 errors
      config.cache = false;
    }
    return config;
  },
};

module.exports = nextConfig;
