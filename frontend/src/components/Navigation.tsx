'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { HomeIcon, CogIcon, DocumentArrowDownIcon, PlayIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '@/stores/authStore'

const navigation = [
  { name: 'ホーム', href: '/', icon: HomeIcon },
  { name: 'アプリ', href: '/app', icon: PlayIcon },
  { name: '設定', href: '/settings', icon: CogIcon },
]

export default function Navigation() {
  const pathname = usePathname()
  const { user, logout, isAuthenticated } = useAuthStore()
  
  const handleLogout = () => {
    logout()
    window.location.href = '/login'
  }

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                <DocumentArrowDownIcon className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">動画会計</span>
            </Link>
            <div className="hidden sm:ml-10 sm:flex sm:space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`inline-flex items-center px-4 py-2 text-sm font-medium transition-colors ${
                      pathname === item.href
                        ? 'text-gray-900'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isAuthenticated && user && (
              <>
                <span className="text-sm text-gray-600">
                  {user.username}
                </span>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
                >
                  <ArrowRightOnRectangleIcon className="h-4 w-4 mr-1" />
                  ログアウト
                </button>
              </>
            )}
            {!isAuthenticated && (
              <Link
                href="/login"
                className="ml-4 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
              >
                ログイン
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}