'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function MasterSettings() {
  const [activeTab, setActiveTab] = useState<'vendors' | 'accounts' | 'rules'>('vendors')
  const queryClient = useQueryClient()

  // Vendors
  const { data: vendors } = useQuery({
    queryKey: ['vendors'],
    queryFn: async () => {
      const res = await api.get('/masters/vendors')
      return res.data
    }
  })

  // Accounts
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const res = await api.get('/masters/accounts')
      return res.data
    }
  })

  // Rules
  const { data: rules } = useQuery({
    queryKey: ['rules'],
    queryFn: async () => {
      const res = await api.get('/masters/rules')
      return res.data
    }
  })

  const addVendorMutation = useMutation({
    mutationFn: async (data: any) => {
      return await api.post('/masters/vendors', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] })
      toast.success('ベンダーを追加しました')
    }
  })

  const addAccountMutation = useMutation({
    mutationFn: async (data: any) => {
      return await api.post('/masters/accounts', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      toast.success('勘定科目を追加しました')
    }
  })

  const addRuleMutation = useMutation({
    mutationFn: async (data: any) => {
      return await api.post('/masters/rules', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      toast.success('ルールを追加しました')
    }
  })

  const [newVendor, setNewVendor] = useState({
    name: '',
    default_debit_account: '',
    default_tax_rate: 0.1
  })

  const [newAccount, setNewAccount] = useState({
    code: '',
    name: '',
    type: '費用'
  })

  const [newRule, setNewRule] = useState({
    pattern: '',
    debit_account: '',
    tax_rate: 0.1,
    priority: 0
  })

  return (
    <div className="space-y-6">
      {/* タブ */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('vendors')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'vendors'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            ベンダーマスタ
          </button>
          <button
            onClick={() => setActiveTab('accounts')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'accounts'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            勘定科目
          </button>
          <button
            onClick={() => setActiveTab('rules')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'rules'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            仕訳ルール
          </button>
        </nav>
      </div>

      {/* ベンダーマスタ */}
      {activeTab === 'vendors' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">ベンダーマスタ</h3>
          
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-medium mb-3">新規追加</h4>
            <div className="grid grid-cols-3 gap-4">
              <input
                type="text"
                placeholder="ベンダー名"
                value={newVendor.name}
                onChange={(e) => setNewVendor({ ...newVendor, name: e.target.value })}
                className="input-field"
              />
              <input
                type="text"
                placeholder="既定借方科目"
                value={newVendor.default_debit_account}
                onChange={(e) => setNewVendor({ ...newVendor, default_debit_account: e.target.value })}
                className="input-field"
              />
              <div className="flex space-x-2">
                <select
                  value={newVendor.default_tax_rate}
                  onChange={(e) => setNewVendor({ ...newVendor, default_tax_rate: parseFloat(e.target.value) })}
                  className="input-field flex-1"
                >
                  <option value="0.1">10%</option>
                  <option value="0.08">8%</option>
                  <option value="0">非課税</option>
                </select>
                <button
                  onClick={() => {
                    addVendorMutation.mutate(newVendor)
                    setNewVendor({ name: '', default_debit_account: '', default_tax_rate: 0.1 })
                  }}
                  className="btn-primary"
                >
                  <PlusIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    ベンダー名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    既定借方科目
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    既定税率
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {vendors?.map((vendor: any) => (
                  <tr key={vendor.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{vendor.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {vendor.default_debit_account || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {vendor.default_tax_rate ? `${Math.round(vendor.default_tax_rate * 100)}%` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button className="text-red-600 hover:text-red-900">
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 勘定科目 */}
      {activeTab === 'accounts' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">勘定科目</h3>
          
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-medium mb-3">新規追加</h4>
            <div className="grid grid-cols-4 gap-4">
              <input
                type="text"
                placeholder="科目コード"
                value={newAccount.code}
                onChange={(e) => setNewAccount({ ...newAccount, code: e.target.value })}
                className="input-field"
              />
              <input
                type="text"
                placeholder="科目名"
                value={newAccount.name}
                onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
                className="input-field"
              />
              <select
                value={newAccount.type}
                onChange={(e) => setNewAccount({ ...newAccount, type: e.target.value })}
                className="input-field"
              >
                <option value="資産">資産</option>
                <option value="負債">負債</option>
                <option value="純資産">純資産</option>
                <option value="収益">収益</option>
                <option value="費用">費用</option>
              </select>
              <button
                onClick={() => {
                  addAccountMutation.mutate(newAccount)
                  setNewAccount({ code: '', name: '', type: '費用' })
                }}
                className="btn-primary"
              >
                <PlusIcon className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    コード
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    科目名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    種別
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {accounts?.map((account: any) => (
                  <tr key={account.code}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{account.code}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{account.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{account.type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 仕訳ルール */}
      {activeTab === 'rules' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">仕訳ルール</h3>
          
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-medium mb-3">新規追加</h4>
            <div className="grid grid-cols-4 gap-4">
              <input
                type="text"
                placeholder="パターン（正規表現）"
                value={newRule.pattern}
                onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
                className="input-field"
              />
              <input
                type="text"
                placeholder="借方科目"
                value={newRule.debit_account}
                onChange={(e) => setNewRule({ ...newRule, debit_account: e.target.value })}
                className="input-field"
              />
              <input
                type="number"
                placeholder="優先度"
                value={newRule.priority}
                onChange={(e) => setNewRule({ ...newRule, priority: parseInt(e.target.value) })}
                className="input-field"
              />
              <button
                onClick={() => {
                  addRuleMutation.mutate(newRule)
                  setNewRule({ pattern: '', debit_account: '', tax_rate: 0.1, priority: 0 })
                }}
                className="btn-primary"
              >
                <PlusIcon className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    パターン
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    借方科目
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    優先度
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {rules?.map((rule: any) => (
                  <tr key={rule.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">{rule.pattern}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{rule.debit_account || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{rule.priority}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button className="text-red-600 hover:text-red-900">
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}