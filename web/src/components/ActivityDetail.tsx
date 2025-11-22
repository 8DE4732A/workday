'use client';

import React from 'react';
import { TimelineCard, categoryColors, CategoryType } from '@/types';
import { formatTimestamp, formatDuration, formatDateTime } from '@/lib/utils';

interface ActivityDetailProps {
  card: TimelineCard | null;
}

export function ActivityDetail({ card }: ActivityDetailProps) {
  if (!card) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-workday-muted">
        <svg
          className="w-24 h-24 mb-4 opacity-20"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-lg">Select an activity</p>
        <p className="text-sm mt-2">Click on an activity to see details</p>
      </div>
    );
  }

  const categoryColor = categoryColors[card.category as CategoryType] || categoryColors['其他'];

  return (
    <div className="h-full overflow-y-auto">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span
              className="inline-block px-3 py-1 rounded text-sm font-medium text-white"
              style={{ backgroundColor: categoryColor }}
            >
              {card.category}
            </span>
            <span className="text-sm text-workday-muted">
              {formatDuration(card.duration)}
            </span>
          </div>

          <h1 className="text-3xl font-serif font-semibold text-workday-text mb-2">
            {card.title}
          </h1>

          <div className="flex items-center gap-2 text-workday-muted">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm">
              {formatTimestamp(card.start_ts)} - {formatTimestamp(card.end_ts)}
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-workday-border" />

        {/* Description */}
        <div>
          <h2 className="text-lg font-semibold text-workday-text mb-3">Description</h2>
          <p className="text-workday-text leading-relaxed whitespace-pre-wrap">
            {card.description || 'No description available.'}
          </p>
        </div>

        {/* Video */}
        {card.video_path && (
          <div>
            <h2 className="text-lg font-semibold text-workday-text mb-3">Recording</h2>
            <div className="bg-black rounded-lg overflow-hidden aspect-video">
              <video
                key={card.id}
                src={`/video/${card.id}`}
                controls
                loop
                autoPlay
                className="w-full h-full"
                preload="metadata"
              >
                Your browser does not support the video tag.
              </video>
            </div>
          </div>
        )}

        {/* Metadata */}
        <div>
          <h2 className="text-lg font-semibold text-workday-text mb-3">Metadata</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-workday-muted">Batch ID</dt>
              <dd className="text-workday-text font-medium">{card.batch_id}</dd>
            </div>
            <div>
              <dt className="text-workday-muted">Card ID</dt>
              <dd className="text-workday-text font-medium">{card.id}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-workday-muted">Start Time</dt>
              <dd className="text-workday-text font-medium">
                {formatDateTime(card.start_ts)}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-workday-muted">End Time</dt>
              <dd className="text-workday-text font-medium">
                {formatDateTime(card.end_ts)}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
