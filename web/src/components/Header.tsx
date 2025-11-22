'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { RecordingStatus } from '@/types';
import { cn } from '@/lib/utils';

interface HeaderProps {
  date: Date;
  onDateChange: (date: Date) => void;
  onRefresh: () => void;
}

interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  request_count: number;
}

export function Header({ date, onDateChange, onRefresh }: HeaderProps) {
  const [recordingStatus, setRecordingStatus] = useState<RecordingStatus | null>(null);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadRecordingStatus();
    loadTokenUsage();
    const interval = setInterval(() => {
      loadRecordingStatus();
      loadTokenUsage();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadRecordingStatus = async () => {
    try {
      const status = await apiClient.getRecordingStatus();
      setRecordingStatus(status);
    } catch (error) {
      console.error('Failed to load recording status:', error);
    }
  };

  const loadTokenUsage = async () => {
    try {
      const usage = await apiClient.getTodayTokenUsage();
      setTokenUsage({
        prompt_tokens: usage.prompt_tokens,
        completion_tokens: usage.completion_tokens,
        total_tokens: usage.total_tokens,
        request_count: usage.request_count,
      });
    } catch (error) {
      console.error('Failed to load token usage:', error);
    }
  };

  const formatTokenCount = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`;
    }
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`;
    }
    return count.toString();
  };

  const toggleRecording = async () => {
    setIsLoading(true);
    try {
      if (recordingStatus?.is_recording) {
        await apiClient.stopRecording();
      } else {
        await apiClient.startRecording();
      }
      await loadRecordingStatus();
    } catch (error) {
      console.error('Failed to toggle recording:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (date: Date) => {
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();

    if (isToday) {
      return 'Today';
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const goToPreviousDay = () => {
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() - 1);
    onDateChange(newDate);
  };

  const goToNextDay = () => {
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() + 1);
    if (newDate <= new Date()) {
      onDateChange(newDate);
    }
  };

  const goToToday = () => {
    onDateChange(new Date());
  };

  const canGoForward = date.toDateString() !== new Date().toDateString();

  return (
    <div className="flex items-center justify-between p-6 bg-white border-b border-workday-border">
      {/* Date navigation */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-4xl font-serif font-semibold text-workday-text min-w-[180px]">
            {formatDate(date)}
          </h1>
          {tokenUsage && tokenUsage.total_tokens > 0 && (
            <div className="flex items-center gap-2">
              {/* Input tokens */}
              <div
                className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded-lg"
                title={`Input: ${tokenUsage.prompt_tokens.toLocaleString()} tokens`}
              >
                <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
                </svg>
                <span className="text-xs text-blue-700 font-medium">{formatTokenCount(tokenUsage.prompt_tokens)}</span>
              </div>

              {/* Output tokens */}
              <div
                className="flex items-center gap-1 px-2 py-1 bg-green-50 rounded-lg"
                title={`Output: ${tokenUsage.completion_tokens.toLocaleString()} tokens`}
              >
                <svg className="w-3.5 h-3.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
                <span className="text-xs text-green-700 font-medium">{formatTokenCount(tokenUsage.completion_tokens)}</span>
              </div>

              {/* Total indicator */}
              <div className="text-xs text-gray-500 font-medium">
                = {formatTokenCount(tokenUsage.total_tokens)}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={goToPreviousDay}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Previous day"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <button
            onClick={goToNextDay}
            disabled={!canGoForward}
            className={cn(
              'p-2 rounded-lg transition-colors',
              canGoForward ? 'hover:bg-gray-100' : 'opacity-30 cursor-not-allowed'
            )}
            title="Next day"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          {!canGoForward && (
            <button
              onClick={goToToday}
              className="ml-2 px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Today
            </button>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={onRefresh}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Refresh"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>

        <button
          onClick={toggleRecording}
          disabled={isLoading}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
            recordingStatus?.is_recording
              ? 'bg-red-500 hover:bg-red-600 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
        >
          <span
            className={cn(
              'w-2 h-2 rounded-full',
              recordingStatus?.is_recording ? 'bg-white animate-pulse' : 'bg-white'
            )}
          />
          <span>{recordingStatus?.is_recording ? 'Recording' : 'Start Recording'}</span>
        </button>
      </div>
    </div>
  );
}
