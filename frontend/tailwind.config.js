/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // プライマリカラー（青系）
        primary: {
          DEFAULT: '#2C5282',  // メインの青
          light: '#3182CE',    // 明るい青
          dark: '#1A365D',     // 暗い青
          50: '#EBF8FF',
          100: '#BEE3F8',
          200: '#90CDF4',
          300: '#63B3ED',
          400: '#4299E1',
          500: '#3182CE',      // primary-light
          600: '#2C5282',      // primary (DEFAULT)
          700: '#2A4E7C',
          800: '#1A365D',      // primary-dark
          900: '#153E75',
        },
        // アクセントカラー
        accent: {
          DEFAULT: '#F97316',  // オレンジ（CTA、強調）
          light: '#FB923C',
          dark: '#EA580C',
        },
        // グレースケール
        gray: {
          50: '#F9FAFB',       // 背景色
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',      // テキスト色
          700: '#374151',
          800: '#1F2937',      // 濃いテキスト
          900: '#111827',
        },
      },
    },
  },
  plugins: [],
}