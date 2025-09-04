'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { 
  ArrowRightIcon,
  CheckIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'

export default function Home() {
  const router = useRouter()

  const features = [
    {
      title: '動画から自動認識',
      description: '領収書を撮影した動画をアップロードするだけで、AIが自動的に領収書を検出・認識します。',
    },
    {
      title: 'OCR文字認識',
      description: 'Google Cloud Vision APIを使用して、領収書の文字を自動認識します。',
    },
    {
      title: '自動仕訳生成',
      description: '認識した内容から会計仕訳を自動生成。手入力の手間を大幅に削減します。',
    },
    {
      title: 'CSV出力対応',
      description: '生成した仕訳データをCSV形式で出力。既存の会計ソフトとの連携も簡単です。',
    },
  ]

  const benefits = [
    '動画から複数の領収書を一括処理',
    '手入力作業を削減',
    'CSVエクスポートで既存システムと連携',
    'いつでもデータを確認・修正可能',
  ]

  return (
    <div className="min-h-screen">
      {/* ヒーローセクション - Linear風 */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 text-center">
          <div className="mx-auto max-w-3xl">
            <div className="mb-8">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-primary-50 text-primary-700 border border-primary-200">
                <SparklesIcon className="h-4 w-4" />
                AI搭載の会計自動化ツール
              </span>
            </div>
            
            <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 tracking-tight">
              領収書処理を
              <span className="block text-primary-600 mt-2">自動化する</span>
            </h1>
            
            <p className="mt-6 text-xl text-gray-600 leading-relaxed max-w-2xl mx-auto">
              動画から領収書を自動認識し、会計仕訳を瞬時に生成。
              経理業務の効率を劇的に向上させます。
            </p>
            
            <div className="mt-10 flex items-center justify-center">
              <Link
                href="/upload"
                className="group inline-flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 transition-colors"
              >
                無料で始める
                <ArrowRightIcon className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </section>


      {/* 機能セクション - シンプルなグリッド */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">
              シンプルで強力な機能
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              複雑な設定は不要。すぐに使い始められます。
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="p-6 rounded-2xl border border-gray-200 hover:border-gray-300 transition-colors"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 使い方セクション - Linear風のステップ */}
      <section className="py-20 bg-gray-50/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">
              3ステップで完了
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              面倒な設定は一切不要です
            </p>
          </div>
          
          <div className="max-w-4xl mx-auto">
            <div className="space-y-12">
              <div className="flex gap-6">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                    1
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    動画をアップロード
                  </h3>
                  <p className="text-gray-600">
                    領収書を撮影した動画をドラッグ&ドロップでアップロード
                  </p>
                </div>
              </div>
              
              <div className="flex gap-6">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                    2
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    AIが自動処理
                  </h3>
                  <p className="text-gray-600">
                    領収書の検出、文字認識、仕訳生成まですべて自動
                  </p>
                </div>
              </div>
              
              <div className="flex gap-6">
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                    3
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    結果を確認・出力
                  </h3>
                  <p className="text-gray-600">
                    認識結果を確認して、CSVで簡単にダウンロード
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ベネフィット */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">
              導入メリット
            </h2>
          </div>
          
          <div className="max-w-2xl mx-auto">
            <div className="space-y-4">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start gap-3">
                  <CheckIcon className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
                  <span className="text-lg text-gray-700">{benefit}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            今すぐ始めてみませんか？
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            クレジットカード不要・無料でお試しいただけます
          </p>
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 px-8 py-4 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 transition-colors"
          >
            無料で始める
            <ArrowRightIcon className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  )
}