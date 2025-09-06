'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

// 履歴アイテムの型定義
export interface JournalHistoryItem {
  id: string
  videoId: number
  videoTitle: string
  currentTime: number
  totalReceipts: number
  totalJournals: number
  createdAt: Date
  lastAccessedAt: Date
  thumbnailUrl?: string
}

// コンテキストの型定義
interface JournalHistoryContextType {
  history: JournalHistoryItem[]
  currentSession: JournalHistoryItem | null
  addToHistory: (item: Omit<JournalHistoryItem, 'id' | 'createdAt' | 'lastAccessedAt'>) => void
  updateCurrentSession: (videoId: number, updates: Partial<JournalHistoryItem>) => void
  removeFromHistory: (id: string) => void
  clearHistory: () => void
  getHistoryItem: (id: string) => JournalHistoryItem | undefined
}

// コンテキストの作成
const JournalHistoryContext = createContext<JournalHistoryContextType | undefined>(undefined)

// ストレージキー
const STORAGE_KEY = 'journal_history'
const MAX_HISTORY_ITEMS = 20 // 最大履歴保存数（増やして永続化）

export function JournalHistoryProvider({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<JournalHistoryItem[]>([])
  const [currentSession, setCurrentSession] = useState<JournalHistoryItem | null>(null)

  // 初回ロード時にローカルストレージから履歴を復元
  useEffect(() => {
    // クライアントサイドでのみ実行
    if (typeof window === 'undefined') return
    
    const loadHistory = () => {
      try {
        const stored = window.localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          // Date型に変換
          const restored = parsed.map((item: any) => ({
            ...item,
            createdAt: new Date(item.createdAt),
            lastAccessedAt: new Date(item.lastAccessedAt)
          }))
          setHistory(restored)
        }
      } catch (error) {
        console.error('Failed to load history:', error)
      }
    }

    loadHistory()
  }, [])

  // 履歴が変更されたらローカルストレージに保存
  useEffect(() => {
    // クライアントサイドでのみ実行
    if (typeof window === 'undefined') return
    
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
    } catch (error) {
      console.error('Failed to save history:', error)
    }
  }, [history])

  // 履歴に追加
  const addToHistory = (item: Omit<JournalHistoryItem, 'id' | 'createdAt' | 'lastAccessedAt'>) => {
    const newItem: JournalHistoryItem = {
      ...item,
      id: `history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date(),
      lastAccessedAt: new Date()
    }

    setHistory(prev => {
      // 同じビデオIDの履歴があれば更新
      const existingIndex = prev.findIndex(h => h.videoId === item.videoId)
      if (existingIndex >= 0) {
        const updated = [...prev]
        updated[existingIndex] = {
          ...updated[existingIndex],
          ...item,
          lastAccessedAt: new Date()
        }
        return updated
      }

      // 新規追加（最大数を超えたら古いものを削除）
      const newHistory = [newItem, ...prev]
      if (newHistory.length > MAX_HISTORY_ITEMS) {
        newHistory.pop()
      }
      return newHistory
    })

    setCurrentSession(newItem)
  }

  // 現在のセッションを更新
  const updateCurrentSession = (videoId: number, updates: Partial<JournalHistoryItem>) => {
    setHistory(prev => 
      prev.map(item => 
        item.videoId === videoId 
          ? { ...item, ...updates, lastAccessedAt: new Date() }
          : item
      )
    )

    if (currentSession?.videoId === videoId) {
      setCurrentSession(prev => prev ? { ...prev, ...updates, lastAccessedAt: new Date() } : null)
    }
  }

  // 履歴から削除
  const removeFromHistory = (id: string) => {
    setHistory(prev => prev.filter(item => item.id !== id))
    if (currentSession?.id === id) {
      setCurrentSession(null)
    }
  }

  // 履歴をクリア
  const clearHistory = () => {
    setHistory([])
    setCurrentSession(null)
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }

  // 特定の履歴アイテムを取得
  const getHistoryItem = (id: string) => {
    return history.find(item => item.id === id)
  }

  return (
    <JournalHistoryContext.Provider
      value={{
        history,
        currentSession,
        addToHistory,
        updateCurrentSession,
        removeFromHistory,
        clearHistory,
        getHistoryItem
      }}
    >
      {children}
    </JournalHistoryContext.Provider>
  )
}

// カスタムフック
export function useJournalHistory() {
  const context = useContext(JournalHistoryContext)
  if (context === undefined) {
    throw new Error('useJournalHistory must be used within a JournalHistoryProvider')
  }
  return context
}