// API Types
export interface TimelineCard {
  id: number;
  batch_id: number;
  title: string;
  description: string;
  start_ts: number;
  end_ts: number;
  category: string;
  video_path: string | null;
  duration: number;
}

export interface RecordingStatus {
  is_recording: boolean;
  output_dir: string;
  chunk_duration: number;
  capture_interval: number;
}

export interface Stats {
  chunks: number;
  batches: number;
  observations: number;
  timeline_cards: number;
}

export type CategoryType = '工作' | '学习' | '娱乐' | '其他';

export const categoryColors: Record<CategoryType, string> = {
  '工作': '#3b82f6',
  '学习': '#10b981',
  '娱乐': '#f59e0b',
  '其他': '#6b7280',
};

// Config Types
export interface ConfigItem {
  key: string;
  value: string;
  type: string;
  category: string;
  description: string;
  is_sensitive?: boolean;
  updated_at?: string;
}

export interface AppConfig {
  recording: {
    capture_interval: number;
    chunk_duration: number;
    quality: number;
    format: string;
    output_dir: string;
    monitor_index: number;
  };
  analysis: {
    interval: number;
    batch_duration: number;
    model: string;
    debug_mode: boolean;
  };
  retention: {
    days: number;
  };
  api: {
    host: string;
    port: number;
    debug: boolean;
  };
  database: {
    path: string;
  };
  secrets: {
    ark_api_key: string;
  };
}

export interface MonitorInfo {
  index: number;
  width: number;
  height: number;
  left: number;
  top: number;
  description: string;
}
