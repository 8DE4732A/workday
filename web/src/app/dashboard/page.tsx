'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';

interface TokenRecord {
  id: number;
  request_type: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  batch_id: number | null;
  created_at: string;
}

export default function DashboardPage() {
  const [records, setRecords] = useState<TokenRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    loadRecords();
  }, [selectedDate, page]);

  const loadRecords = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getTokenUsageRecords(
        selectedDate || undefined,
        limit,
        page * limit
      );
      setRecords(response.records);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to load token records:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  const getRequestTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'chat_with_video': '视频分析',
      'generate_activity_cards': '生成活动卡片',
    };
    return labels[type] || type;
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="p-8 bg-workday-panel h-full overflow-y-auto">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-semibold text-workday-text mb-2">Dashboard</h1>
        <p className="text-workday-muted">Token usage records and statistics</p>
      </div>

      {/* Filter Section */}
      <div className="bg-white rounded-lg p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-workday-text">Filter by Date:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => {
              setSelectedDate(e.target.value);
              setPage(0);
            }}
            className="px-3 py-2 border border-workday-border rounded-lg"
          />
          {selectedDate && (
            <button
              onClick={() => {
                setSelectedDate('');
                setPage(0);
              }}
              className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Clear Filter
            </button>
          )}
          <div className="ml-auto text-sm text-workday-muted">
            Total Records: {formatNumber(total)}
          </div>
        </div>
      </div>

      {/* Token Records Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-workday-muted">Loading...</div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center text-workday-muted">No records found</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-workday-border">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Model
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Input Tokens
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Output Tokens
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total Tokens
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Batch ID
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDateTime(record.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {getRequestTypeLabel(record.request_type)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-mono">
                        {record.model}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-blue-600 font-medium">
                        {formatNumber(record.prompt_tokens)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600 font-medium">
                        {formatNumber(record.completion_tokens)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 font-semibold">
                        {formatNumber(record.total_tokens)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-500">
                        {record.batch_id || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="px-6 py-4 bg-gray-50 border-t border-workday-border flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {formatNumber(total)} records
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {page + 1} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
