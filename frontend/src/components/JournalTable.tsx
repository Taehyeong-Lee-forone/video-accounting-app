'use client'

import { useState } from 'react'
import { CheckIcon, XMarkIcon, PencilIcon } from '@heroicons/react/24/outline'

interface JournalTableProps {
  journals: any[]
  onRowClick: (journal: any) => void
  onConfirm: (id: number) => void
  onReject: (id: number) => void
  onUpdate: (id: number, data: any) => void
  selectedId?: number
}

export default function JournalTable({
  journals,
  onRowClick,
  onConfirm,
  onReject,
  onUpdate,
  selectedId
}: JournalTableProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editData, setEditData] = useState<any>({})

  const handleEdit = (journal: any) => {
    setEditingId(journal.id)
    setEditData({
      debit_account: journal.debit_account,
      credit_account: journal.credit_account,
      debit_amount: journal.debit_amount,
      credit_amount: journal.credit_amount,
      memo: journal.memo
    })
  }

  const handleSave = () => {
    if (editingId) {
      onUpdate(editingId, editData)
      setEditingId(null)
      setEditData({})
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setEditData({})
  }

  const statusColors = {
    unconfirmed: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
    pending: 'bg-gray-100 text-gray-800'
  }

  const statusLabels = {
    unconfirmed: '未確認',
    confirmed: '確認済',
    rejected: '差戻し',
    pending: '保留'
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              ステータス
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              借方科目
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              借方金額
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              貸方科目
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              貸方金額
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              メモ
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {journals.map((journal) => {
            const isEditing = editingId === journal.id
            const isSelected = selectedId === journal.id
            
            return (
              <tr
                key={journal.id}
                onClick={() => !isEditing && onRowClick(journal)}
                className={`cursor-pointer hover:bg-gray-50 ${
                  isSelected ? 'bg-blue-50' : ''
                }`}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                    statusColors[journal.status]
                  }`}>
                    {statusLabels[journal.status]}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editData.debit_account}
                      onChange={(e) => setEditData({ ...editData, debit_account: e.target.value })}
                      className="input-field text-sm"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    journal.debit_account || '-'
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {isEditing ? (
                    <input
                      type="number"
                      value={editData.debit_amount}
                      onChange={(e) => setEditData({ ...editData, debit_amount: parseFloat(e.target.value) })}
                      className="input-field text-sm"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    `¥${journal.debit_amount?.toLocaleString() || '0'}`
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editData.credit_account}
                      onChange={(e) => setEditData({ ...editData, credit_account: e.target.value })}
                      className="input-field text-sm"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    journal.credit_account || '-'
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {isEditing ? (
                    <input
                      type="number"
                      value={editData.credit_amount}
                      onChange={(e) => setEditData({ ...editData, credit_amount: parseFloat(e.target.value) })}
                      className="input-field text-sm"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    `¥${journal.credit_amount?.toLocaleString() || '0'}`
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editData.memo}
                      onChange={(e) => setEditData({ ...editData, memo: e.target.value })}
                      className="input-field text-sm"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <span className="truncate block max-w-xs">
                      {journal.memo || '-'}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex space-x-2" onClick={(e) => e.stopPropagation()}>
                    {isEditing ? (
                      <>
                        <button
                          onClick={handleSave}
                          className="text-green-600 hover:text-green-900"
                        >
                          保存
                        </button>
                        <button
                          onClick={handleCancel}
                          className="text-gray-600 hover:text-gray-900"
                        >
                          キャンセル
                        </button>
                      </>
                    ) : (
                      <>
                        {journal.status !== 'confirmed' && (
                          <button
                            onClick={() => onConfirm(journal.id)}
                            className="text-green-600 hover:text-green-900"
                            title="確認"
                          >
                            <CheckIcon className="h-5 w-5" />
                          </button>
                        )}
                        {journal.status !== 'rejected' && (
                          <button
                            onClick={() => onReject(journal.id)}
                            className="text-red-600 hover:text-red-900"
                            title="差戻し"
                          >
                            <XMarkIcon className="h-5 w-5" />
                          </button>
                        )}
                        <button
                          onClick={() => handleEdit(journal)}
                          className="text-blue-600 hover:text-blue-900"
                          title="編集"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}