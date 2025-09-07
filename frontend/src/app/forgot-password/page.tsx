'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { API_BASE_URL } from '@/config/api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email) {
      toast.error('メールアドレスを入力してください')
      return
    }

    // 基本的なメール形式検証
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      toast.error('有効なメールアドレスを入力してください')
      return
    }

    setIsLoading(true)

    try {
      // バックエンドAPIを呼び出す
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })
      
      const data = await response.json()
      
      if (response.ok && data.success) {
        // 成功メッセージを表示
        setIsSubmitted(true)
        toast.success('パスワードリセットメールを送信しました')
        
        // デモモードの場合はトークンを表示
        if (data.message && data.message.includes('デモモード')) {
          console.log('Reset token:', data.message)
        }
      } else {
        throw new Error(data.detail || 'リセットメールの送信に失敗しました')
      }
      
    } catch (error) {
      toast.error('エラーが発生しました。もう一度お試しください。')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white py-8 px-4 shadow-xl rounded-lg sm:px-10">
          <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <h2 className="text-center text-3xl font-extrabold text-gray-900">
              パスワードリセット
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              登録されたメールアドレスを入力してください
            </p>
          </div>

          {!isSubmitted ? (
            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  メールアドレス
                </label>
                <div className="mt-1">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    placeholder="メールアドレスを入力"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                >
                  {isLoading ? (
                    <div className="flex items-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      送信中...
                    </div>
                  ) : (
                    'リセットメールを送信'
                  )}
                </button>
              </div>

              <div className="flex items-center justify-center">
                <Link
                  href="/login"
                  className="flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-500"
                >
                  <ArrowLeftIcon className="h-4 w-4 mr-1" />
                  ログイン画面に戻る
                </Link>
              </div>
            </form>
          ) : (
            <div className="mt-8 space-y-6">
              <div className="rounded-md bg-green-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">
                      メール送信完了
                    </h3>
                    <div className="mt-2 text-sm text-green-700">
                      <p>
                        {email} 宛にパスワードリセット用のメールを送信しました。
                      </p>
                      <p className="mt-1">
                        メールが届かない場合は、迷惑メールフォルダをご確認ください。
                      </p>
                    </div>
                  </div>
                </div>
              </div>


              <div className="flex items-center justify-center">
                <Link
                  href="/login"
                  className="flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-500"
                >
                  <ArrowLeftIcon className="h-4 w-4 mr-1" />
                  ログイン画面に戻る
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}