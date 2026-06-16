'use client';
import React from 'react';
import { Syne } from 'next/font/google';
import ReactMarkdown from 'react-markdown';

type Props = {
  analysis?: string;
  nutrition?: string;
  recuperation?: string;
};

const syne = Syne({ subsets: ['latin'], weight: ['700'] });

export default function AnalysisBox({ analysis, nutrition, recuperation }: Props) {
  const items = [
    { title: 'Análisis', content: analysis },
    { title: 'Nutrición', content: nutrition },
    { title: 'Recuperación', content: recuperation },
  ];

  return (
    <>
      {items.map(({ title, content }, idx) =>
        content ? (
          <div className="card training-analysis" key={idx}>
            <h4 className={`card-title ${syne.className}`}>{title}</h4>
              <div className="analysis-content prose prose-sm prose-neutral max-w-none text-left not-italic">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          </div>
        ) : null
      )}
    </>
  );
}
