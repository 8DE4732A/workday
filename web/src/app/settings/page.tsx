'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { AppConfig, MonitorInfo } from '@/types';

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [monitors, setMonitors] = useState<MonitorInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    captureInterval: 1,
    chunkDuration: 15,
    quality: 85,
    monitorIndex: 0,
    analysisInterval: 15,
    batchDuration: 15,
    model: '',
    retentionDays: 3,
    arkApiKey: '',
    debugMode: false,
  });

  // Track if API key has been modified
  const [apiKeyModified, setApiKeyModified] = useState(false);

  useEffect(() => {
    loadConfig();
    loadMonitors();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await apiClient.getConfig(true);
      setConfig(data);
      setFormData({
        captureInterval: data.recording.capture_interval,
        chunkDuration: data.recording.chunk_duration,
        quality: data.recording.quality,
        monitorIndex: data.recording.monitor_index,
        analysisInterval: data.analysis.interval,
        batchDuration: data.analysis.batch_duration,
        model: data.analysis.model,
        retentionDays: data.retention.days,
        arkApiKey: data.secrets.ark_api_key,
        debugMode: data.analysis.debug_mode || false,
      });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to load configuration' });
    } finally {
      setLoading(false);
    }
  };

  const loadMonitors = async () => {
    try {
      const data = await apiClient.getMonitors();
      if (data.success) {
        setMonitors(data.monitors);
      }
    } catch (error) {
      console.error('Failed to load monitors:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const configs: Record<string, string> = {
        'recording.capture_interval': String(formData.captureInterval),
        'recording.chunk_duration': String(formData.chunkDuration),
        'recording.quality': String(formData.quality),
        'recording.monitor_index': String(formData.monitorIndex),
        'analysis.interval': String(formData.analysisInterval),
        'analysis.batch_duration': String(formData.batchDuration),
        'analysis.model': formData.model,
        'analysis.debug_mode': String(formData.debugMode),
        'retention.days': String(formData.retentionDays),
      };

      // Only update API key if it was modified and is not a masked value
      if (apiKeyModified && formData.arkApiKey && !formData.arkApiKey.includes('*')) {
        configs['secrets.ark_api_key'] = formData.arkApiKey;
      }

      const result = await apiClient.batchUpdateConfigs(configs);

      if (result.success) {
        setMessage({ type: 'success', text: 'Configuration saved successfully' });
        setApiKeyModified(false);
        // Reload config to get updated masked values
        await loadConfig();
      } else if (result.errors && result.errors.length > 0) {
        setMessage({
          type: 'error',
          text: `Some settings failed: ${result.errors.map(e => e.error).join(', ')}`
        });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save configuration' });
    } finally {
      setSaving(false);
    }
  };

  const handleClearData = async () => {
    if (!confirm('Are you sure you want to clear all data? This will delete all recordings, analysis results, and video files. This action cannot be undone.')) {
      return;
    }

    setClearing(true);
    setMessage(null);

    try {
      const result = await apiClient.clearAllData(false);

      if (result.success) {
        const deleted = result.deleted;
        setMessage({
          type: 'success',
          text: `Cleared: ${deleted.chunks} chunks, ${deleted.batches} batches, ${deleted.timeline_cards} cards, ${deleted.observations} observations, ${deleted.token_usage} token records. Deleted ${result.deleted_files} video files.`
        });
      } else {
        setMessage({ type: 'error', text: 'Failed to clear data' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to clear data' });
    } finally {
      setClearing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 bg-workday-panel h-full flex items-center justify-center">
        <div className="text-workday-muted">Loading configuration...</div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-workday-panel h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-4xl font-serif font-semibold text-workday-text">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}

      <div className="max-w-2xl space-y-6">
        {/* API Key Settings */}
        <section className="bg-white rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-workday-text mb-4">API Configuration</h2>
          <div>
            <label className="block text-sm font-medium text-workday-text mb-1">
              ARK API Key
            </label>
            <p className="text-sm text-workday-muted mb-2">
              Your Volcano Engine ARK API key for LLM analysis
            </p>
            <input
              type="password"
              value={formData.arkApiKey}
              onChange={(e) => {
                setFormData({ ...formData, arkApiKey: e.target.value });
                setApiKeyModified(true);
              }}
              placeholder="Enter your API key"
              className="w-full px-3 py-2 border border-workday-border rounded-lg font-mono text-sm"
            />
            <p className="text-xs text-workday-muted mt-1">
              Get your API key from{' '}
              <a
                href="https://console.volcengine.com/ark"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                Volcano Engine Console
              </a>
            </p>
          </div>
        </section>

        {/* Recording Settings */}
        <section className="bg-white rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-workday-text mb-4">Recording</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Monitor
              </label>
              <p className="text-sm text-workday-muted mb-2">
                Select which monitor to record
              </p>
              <select
                value={formData.monitorIndex}
                onChange={(e) => setFormData({ ...formData, monitorIndex: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-workday-border rounded-lg"
              >
                {monitors.length > 0 ? (
                  monitors.map((monitor) => (
                    <option key={monitor.index} value={monitor.index}>
                      {monitor.description} ({monitor.width}x{monitor.height})
                    </option>
                  ))
                ) : (
                  <option value={0}>All monitors</option>
                )}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Capture Interval
              </label>
              <p className="text-sm text-workday-muted mb-2">
                How often to capture screenshots (in seconds)
              </p>
              <input
                type="number"
                value={formData.captureInterval}
                onChange={(e) => setFormData({ ...formData, captureInterval: parseInt(e.target.value) || 1 })}
                className="w-32 px-3 py-2 border border-workday-border rounded-lg"
                min={1}
                max={60}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Chunk Duration
              </label>
              <p className="text-sm text-workday-muted mb-2">
                Duration of each recording chunk (in seconds)
              </p>
              <input
                type="number"
                value={formData.chunkDuration}
                onChange={(e) => setFormData({ ...formData, chunkDuration: parseInt(e.target.value) || 15 })}
                className="w-32 px-3 py-2 border border-workday-border rounded-lg"
                min={10}
                max={60}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Quality
              </label>
              <p className="text-sm text-workday-muted mb-2">
                Image quality for screenshots (1-100)
              </p>
              <input
                type="number"
                value={formData.quality}
                onChange={(e) => setFormData({ ...formData, quality: parseInt(e.target.value) || 85 })}
                className="w-32 px-3 py-2 border border-workday-border rounded-lg"
                min={1}
                max={100}
              />
            </div>
          </div>
        </section>

        {/* Analysis Settings */}
        <section className="bg-white rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-workday-text mb-4">Analysis</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Analysis Interval
              </label>
              <p className="text-sm text-workday-muted mb-2">
                How often to analyze recordings (in minutes)
              </p>
              <input
                type="number"
                value={formData.analysisInterval}
                onChange={(e) => setFormData({ ...formData, analysisInterval: parseInt(e.target.value) || 15 })}
                className="w-32 px-3 py-2 border border-workday-border rounded-lg"
                min={5}
                max={60}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Batch Duration
              </label>
              <p className="text-sm text-workday-muted mb-2">
                Duration of each analysis batch (in minutes)
              </p>
              <input
                type="number"
                value={formData.batchDuration}
                onChange={(e) => setFormData({ ...formData, batchDuration: parseInt(e.target.value) || 15 })}
                className="w-32 px-3 py-2 border border-workday-border rounded-lg"
                min={5}
                max={60}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-workday-text mb-1">
                Model
              </label>
              <p className="text-sm text-workday-muted mb-2">
                AI model to use for analysis
              </p>
              <input
                type="text"
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                className="w-full px-3 py-2 border border-workday-border rounded-lg"
              />
            </div>

            <div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.debugMode}
                  onChange={(e) => setFormData({ ...formData, debugMode: e.target.checked })}
                  className="w-5 h-5 rounded border-workday-border text-blue-500 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-workday-text">Debug Mode</span>
              </label>
              <p className="text-sm text-workday-muted mt-1 ml-8">
                Skip LLM calls and generate default summaries. Useful for testing without consuming tokens.
              </p>
            </div>
          </div>
        </section>

        {/* Debug Tools */}
        <section className="bg-white rounded-lg p-6 shadow-sm border-2 border-orange-200">
          <h2 className="text-xl font-semibold text-workday-text mb-4">Debug Tools</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-workday-muted mb-3">
                Clear all data including recordings, analysis results, and video files. Configuration will be preserved.
              </p>
              <button
                onClick={handleClearData}
                disabled={clearing}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {clearing ? 'Clearing...' : 'Clear All Data'}
              </button>
            </div>
          </div>
        </section>

        {/* Data Retention */}
        <section className="bg-white rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-workday-text mb-4">Data Retention</h2>
          <div>
            <label className="block text-sm font-medium text-workday-text mb-1">
              Retention Days
            </label>
            <p className="text-sm text-workday-muted mb-2">
              Number of days to keep recording data
            </p>
            <input
              type="number"
              value={formData.retentionDays}
              onChange={(e) => setFormData({ ...formData, retentionDays: parseInt(e.target.value) || 3 })}
              className="w-32 px-3 py-2 border border-workday-border rounded-lg"
              min={1}
              max={30}
            />
          </div>
        </section>

        {/* About */}
        <section className="bg-white rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-workday-text mb-4">About</h2>
          <div className="space-y-2 text-sm text-workday-muted">
            <p><strong>Version:</strong> 0.1.0</p>
            <p><strong>Backend:</strong> Python FastAPI</p>
            <p><strong>Frontend:</strong> Next.js</p>
            <p className="pt-4">
              Workday is an AI-powered timeline tracker inspired by{' '}
              <a
                href="https://github.com/dayflow-ai/dayflow"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                Dayflow
              </a>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
