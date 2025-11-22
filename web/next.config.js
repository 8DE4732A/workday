/** @type {import('next').NextConfig} */
const nextConfig = {
  // 静态导出配置
  output: 'export',
  distDir: 'out',

  // 图片优化配置（静态导出需要禁用）
  images: {
    unoptimized: true,
  },

  // 路径配置
  trailingSlash: true,

  // 确保所有页面都构建为静态 HTML
  generateBuildId: async () => {
    return 'build-' + Date.now()
  },
}

module.exports = nextConfig
