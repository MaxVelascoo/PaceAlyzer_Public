import React from 'react';

export default function WeekHeader({
  diasConFechas,
  diaSeleccionado,
  semanaOffset,
  onDiaClick,
  onPrev,
  onNext
}: {
  diasConFechas: { nombre: string; key: string; numero: number }[];
  diaSeleccionado: number;
  semanaOffset: number;
  onDiaClick: (i: number) => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="week-header">
      <button className="nav-button" onClick={onPrev}>‹</button>
      <div className="days-scroll">
        {diasConFechas.map((d, i) => (
          <button
            key={d.key}
            className={`day-pill ${i === diaSeleccionado ? 'active' : ''}`}
            onClick={() => onDiaClick(i)}
          >
            <div style={{ fontSize: '0.75rem', lineHeight: '1rem', marginBottom: '2px', opacity: 0.7 }}>{d.numero}</div>
            <div>{d.nombre}</div>
          </button>
        ))}
      </div>
      <button className="nav-button" onClick={onNext} disabled={semanaOffset === 0}>›</button>
    </div>
  );
}
