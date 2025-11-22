'use client';

import { useState, useEffect, useCallback } from 'react';
import { TimelineCard } from '@/types';
import { apiClient } from '@/lib/api';
import { Header } from '@/components/Header';
import { TimelineList } from '@/components/TimelineList';
import { ActivityDetail } from '@/components/ActivityDetail';
import { formatDate } from '@/lib/utils';

export default function Home() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [cards, setCards] = useState<TimelineCard[]>([]);
  const [selectedCard, setSelectedCard] = useState<TimelineCard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTimeline = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const day = formatDate(Math.floor(selectedDate.getTime() / 1000));
      const timeline = await apiClient.getTimelineByDay(day);
      setCards(timeline);

      // Auto-select first card if none selected or if selected card is not in new timeline
      if (timeline.length > 0) {
        if (!selectedCard || !timeline.find((c) => c.id === selectedCard.id)) {
          setSelectedCard(timeline[0]);
        }
      } else {
        setSelectedCard(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
      console.error('Failed to load timeline:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedDate, selectedCard]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const handleDateChange = (date: Date) => {
    setSelectedDate(date);
    setSelectedCard(null);
  };

  const handleRefresh = () => {
    loadTimeline();
  };

  const handleCardSelect = (card: TimelineCard) => {
    setSelectedCard(card);
  };

  return (
    <div className="flex flex-col h-full bg-workday-panel">
      {/* Header */}
      <Header
        date={selectedDate}
        onDateChange={handleDateChange}
        onRefresh={handleRefresh}
      />

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Timeline list */}
        <div className="w-[400px] flex-shrink-0 border-r border-workday-border overflow-y-auto p-6">
          {isLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-workday-text"></div>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
              <p className="font-medium">Error</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {!isLoading && !error && (
            <TimelineList
              cards={cards}
              selectedId={selectedCard?.id}
              onSelect={handleCardSelect}
            />
          )}
        </div>

        {/* Right: Activity detail */}
        <div className="flex-1 overflow-y-auto p-8">
          <ActivityDetail card={selectedCard} />
        </div>
      </div>
    </div>
  );
}
