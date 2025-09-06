import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'
import { Toaster } from 'react-hot-toast'
import Navigation from '@/components/Navigation'
import AuthProvider from '@/components/AuthProvider'
import { JournalHistoryProvider } from '@/contexts/JournalHistoryContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '動画会計アプリ',
  description: '領収書動画から自動仕訳を生成',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className={inter.className}>
        <Providers>
          <AuthProvider>
            <JournalHistoryProvider>
              <div className="min-h-screen bg-gray-50">
                <Navigation />
                <main className="container mx-auto px-4 py-8">
                  {children}
                </main>
              </div>
            </JournalHistoryProvider>
          </AuthProvider>
          <Toaster 
            position="bottom-left"
            toastOptions={{
              duration: 3000,
              style: {
                background: '#363636',
                color: '#fff',
                zIndex: 9999,
              },
              success: {
                style: {
                  background: '#10b981',
                },
                iconTheme: {
                  primary: '#fff',
                  secondary: '#10b981',
                },
              },
              error: {
                style: {
                  background: '#ef4444',
                },
                iconTheme: {
                  primary: '#fff',
                  secondary: '#ef4444',
                },
              },
            }}
          />
        </Providers>
      </body>
    </html>
  )
}