// API Client
import type { TimelineCard, RecordingStatus, Stats, AppConfig, ConfigItem, MonitorInfo } from '@/types';

// For static export, we default to empty string to use relative URLs
// This allows the static site to work when served from the same origin as the API
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Recording APIs
  async startRecording() {
    return this.request('/recording/start', { method: 'POST' });
  }

  async stopRecording() {
    return this.request('/recording/stop', { method: 'POST' });
  }

  async getRecordingStatus(): Promise<RecordingStatus> {
    return this.request<RecordingStatus>('/recording/status');
  }

  async getMonitors(): Promise<{ success: boolean; monitors: MonitorInfo[] }> {
    return this.request('/recording/monitors');
  }

  // Timeline APIs
  async getTodayTimeline(): Promise<TimelineCard[]> {
    return this.request<TimelineCard[]>('/timeline/today');
  }

  async getTimelineByDay(day: string): Promise<TimelineCard[]> {
    return this.request<TimelineCard[]>(`/timeline/day/${day}`);
  }

  async getTimelineByRange(start_ts: number, end_ts: number): Promise<TimelineCard[]> {
    return this.request<TimelineCard[]>(`/timeline/range?start_ts=${start_ts}&end_ts=${end_ts}`);
  }

  // Analysis APIs
  async triggerAnalysis() {
    return this.request('/analysis/trigger', { method: 'POST' });
  }

  async reprocessDay(day: string) {
    return this.request('/analysis/reprocess', {
      method: 'POST',
      body: JSON.stringify({ day }),
    });
  }

  // Stats APIs
  async getStats(): Promise<Stats> {
    return this.request<Stats>('/stats');
  }

  // Config APIs
  async getConfig(maskSensitive: boolean = true): Promise<AppConfig> {
    return this.request<AppConfig>(`/config?mask_sensitive=${maskSensitive}`);
  }

  async getAllConfigs(maskSensitive: boolean = true): Promise<Record<string, ConfigItem>> {
    return this.request<Record<string, ConfigItem>>(`/config/all?mask_sensitive=${maskSensitive}`);
  }

  async getConfigItem(key: string, maskSensitive: boolean = true): Promise<{
    key: string;
    value: string | number | boolean;
    is_sensitive: boolean;
    metadata: ConfigItem;
  }> {
    return this.request(`/config/${key}?mask_sensitive=${maskSensitive}`);
  }

  async updateConfig(key: string, value: string): Promise<{
    success: boolean;
    message: string;
    key: string;
    value: string;
  }> {
    return this.request(`/config/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ key, value }),
    });
  }

  async batchUpdateConfigs(configs: Record<string, string>): Promise<{
    success: boolean;
    updated: string[];
    errors: Array<{ key: string; error: string }>;
  }> {
    return this.request('/config/batch', {
      method: 'POST',
      body: JSON.stringify({ configs }),
    });
  }

  async reloadConfig(): Promise<{ success: boolean; message: string }> {
    return this.request('/config/reload', { method: 'POST' });
  }

  // Data Management APIs
  async clearAllData(keepVideos: boolean = false): Promise<{
    success: boolean;
    deleted: {
      chunks: number;
      batches: number;
      observations: number;
      timeline_cards: number;
      token_usage: number;
    };
    deleted_files: number;
    failed_files: string[];
  }> {
    return this.request('/data/clear', {
      method: 'POST',
      body: JSON.stringify({ keep_videos: keepVideos }),
    });
  }

  // Token Usage APIs
  async getTodayTokenUsage(): Promise<{
    date: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    request_count: number;
  }> {
    return this.request('/stats/token/today');
  }

  async getTokenUsageRange(startDate: string, endDate: string): Promise<{
    start_date: string;
    end_date: string;
    daily_usage: Array<{
      date: string;
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      request_count: number;
    }>;
    total: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      request_count: number;
    };
  }> {
    return this.request(`/stats/token/range?start_date=${startDate}&end_date=${endDate}`);
  }

  async getTokenUsageRecords(date?: string, limit: number = 100, offset: number = 0): Promise<{
    records: Array<{
      id: number;
      request_type: string;
      model: string;
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      batch_id: number | null;
      created_at: string;
    }>;
    total: number;
    limit: number;
    offset: number;
  }> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (date) {
      params.append('date', date);
    }
    return this.request(`/stats/token/records?${params.toString()}`);
  }
}

export const apiClient = new APIClient();
