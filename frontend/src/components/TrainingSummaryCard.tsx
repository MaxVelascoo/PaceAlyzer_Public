import React from 'react';
import { Syne } from 'next/font/google';

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

type Training = {
  activity_id: number;
  name: string;
  date: string;
  distance: number;
  duration: number;
  avgheartrate: number | null;
  avgpower: number | null;
  weighted_avg_watts: number | null;
};

export default function TrainingSummaryCard({ training }: { training: Training }) {
  return (
    <div className="card training-summary">
      <h3 className={`card-title ${syne.className}`}>{training.name}</h3>
      <ul className="summary-list">
        <li>
          <span className="label">Distancia:</span>
          <span>{(training.distance / 1000).toFixed(1)} km</span>
        </li>
        <li>
          <span className="label">Duración:</span>
          <span>
            {Math.floor(training.duration / 3600)}h {Math.floor((training.duration % 3600) / 60)}min
          </span>

        </li>
        {training.avgheartrate && (
          <li>
            <span className="label">FC media:</span>
            <span>{training.avgheartrate} ppm</span>
          </li>
        )}
        {training.avgpower && (
          <li>
            <span className="label">Potencia media:</span>
            <span>{training.avgpower} W</span>
          </li>
        )}
        {training.weighted_avg_watts && (
          <li>
            <span className="label">Potencia normalizada:</span>
            <span>{Math.round(training.weighted_avg_watts)} W</span>
          </li>
        )}
      </ul>
    </div>
  );
}
