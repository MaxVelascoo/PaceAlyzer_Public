'use client';
import React from 'react';
import {
  BoltIcon, // para "Actividad (deporte)"
  CpuChipIcon, // análisis IA
  EnvelopeIcon // notificación (carta)
} from '@heroicons/react/24/outline';
import './styles.css';

export default function WorkflowVisual() {
  return (
    <div className="workflow-visual">
      <h3 className="workflow-title">¿Cómo funciona PaceAlyzer?</h3>

      <div className="workflow-nodes">
        <div className="workflow-node">
          <BoltIcon className="workflow-icon" />
          <span>Actividad registrada</span>
        </div>

        <div className="workflow-arrow">→</div>

        <div className="workflow-node">
          <CpuChipIcon className="workflow-icon" />
          <span>Análisis con IA</span>
        </div>

        <div className="workflow-arrow">→</div>

        <div className="workflow-node">
          <EnvelopeIcon className="workflow-icon" />
          <span>Notificación personalizada</span>
        </div>
      </div>
    </div>
  );
}
