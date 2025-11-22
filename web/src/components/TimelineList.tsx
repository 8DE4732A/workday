'use client';

import React from 'react';
import { TimelineCard, categoryColors, CategoryType } from '@/types';
import { formatTimestamp, formatDuration, cn } from '@/lib/utils';

interface TimelineListProps {
  cards: TimelineCard[];
  selectedId?: number;
  onSelect: (card: TimelineCard) => void;
}

export function TimelineList({ cards, selectedId, onSelect }: TimelineListProps) {
  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-workday-muted">
        <p className="text-lg">No activities yet</p>
        <p className="text-sm mt-2">Start recording to see your timeline</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {cards.map((card) => {
        const isSelected = card.id === selectedId;
        const categoryColor = categoryColors[card.category as CategoryType] || categoryColors['其他'];

        return (
          <button
            key={card.id}
            onClick={() => onSelect(card)}
            className={cn(
              'w-full text-left p-4 rounded-lg transition-all',
              'hover:shadow-md',
              isSelected
                ? 'bg-white shadow-lg ring-2 ring-offset-2'
                : 'bg-white shadow-sm hover:shadow-md'
            )}
            style={{
              '--tw-ring-color': isSelected ? categoryColor : undefined,
            } as React.CSSProperties}
          >
            {/* Time range */}
            <div className="flex items-center gap-2 text-sm text-workday-muted mb-2">
              <span>{formatTimestamp(card.start_ts)}</span>
              <span>-</span>
              <span>{formatTimestamp(card.end_ts)}</span>
              <span className="ml-auto font-medium">{formatDuration(card.duration)}</span>
            </div>

            {/* Title */}
            <h3 className="font-semibold text-workday-text mb-1 line-clamp-1">
              {card.title}
            </h3>

            {/* Category badge */}
            <div className="flex items-center gap-2 mt-2">
              <span
                className="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
                style={{ backgroundColor: categoryColor }}
              >
                {card.category}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
