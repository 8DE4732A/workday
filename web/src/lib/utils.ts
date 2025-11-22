// Utility functions
import { format, formatDistance } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export function formatTimestamp(ts: number): string {
  return format(new Date(ts * 1000), 'HH:mm');
}

export function formatDate(ts: number): string {
  return format(new Date(ts * 1000), 'yyyy-MM-dd');
}

export function formatDateTime(ts: number): string {
  return format(new Date(ts * 1000), 'yyyy-MM-dd HH:mm:ss');
}

export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

export function formatRelativeTime(ts: number): string {
  return formatDistance(new Date(ts * 1000), new Date(), {
    addSuffix: true,
    locale: zhCN,
  });
}

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
