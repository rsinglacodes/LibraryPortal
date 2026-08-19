'use client';

import React from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content) return null;

  // Split into lines/blocks
  const lines = content.split('\n');
  const renderedElements: React.ReactNode[] = [];

  let inList: 'ul' | 'ol' | null = null;
  let listItems: React.ReactNode[] = [];
  let inTable = false;
  let tableRows: string[][] = [];
  let tableHeader: string[] = [];

  const flushList = () => {
    if (inList && listItems.length > 0) {
      if (inList === 'ul') {
        renderedElements.push(
          <ul key={`ul-${renderedElements.length}`} className="list-disc list-inside space-y-1 my-2 pl-2 text-ink-muted">
            {listItems}
          </ul>
        );
      } else {
        renderedElements.push(
          <ol key={`ol-${renderedElements.length}`} className="list-decimal list-inside space-y-1 my-2 pl-2 text-ink-muted">
            {listItems}
          </ol>
        );
      }
      inList = null;
      listItems = [];
    }
  };

  const flushTable = () => {
    if (inTable && tableHeader.length > 0) {
      renderedElements.push(
        <div key={`tbl-${renderedElements.length}`} className="portal-table-wrap">
          <table className="w-full text-left text-xs">
            <thead className="bg-navy border-b border-parchment text-ink font-semibold">
              <tr>
                {tableHeader.map((h, hIdx) => (
                  <th key={hIdx} className="p-2.5">
                    {parseInlineMarkdown(h.trim())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-parchment text-ink">
              {tableRows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-cream-light">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="p-2.5">
                      {parseInlineMarkdown(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      inTable = false;
      tableHeader = [];
      tableRows = [];
    }
  };

  const parseInlineMarkdown = (text: string): React.ReactNode => {
    if (!text) return null;

    // Process bold (**text**), italic (*text* or _text_), code (`text`)
    const parts: React.ReactNode[] = [];
    // Regex matching **bold**, *italic*, `code`
    const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      const matchIndex = match.index;
      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      const matchedStr = match[0];
      if (matchedStr.startsWith('**') && matchedStr.endsWith('**')) {
        parts.push(
          <strong key={`b-${matchIndex}`} className="font-bold text-ink">
            {matchedStr.slice(2, -2)}
          </strong>
        );
      } else if (matchedStr.startsWith('*') && matchedStr.endsWith('*')) {
        parts.push(
          <em key={`i-${matchIndex}`} className="italic text-ink-muted">
            {matchedStr.slice(1, -1)}
          </em>
        );
      } else if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
        parts.push(
          <code key={`c-${matchIndex}`} className="px-1.5 py-0.5 rounded bg-parchment font-mono text-[11px] text-navy border border-parchment-dark">
            {matchedStr.slice(1, -1)}
          </code>
        );
      }
      lastIndex = matchIndex + matchedStr.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // Table Row detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushList();
      const cells = trimmed
        .slice(1, -1)
        .split('|')
        .map((c) => c.trim());

      // Check if it's separator row (e.g. |---|---|)
      if (cells.every((c) => /^:?-+:?$/.test(c))) {
        continue;
      }

      if (!inTable) {
        inTable = true;
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    } else if (inTable) {
      flushTable();
    }

    // Headers
    if (trimmed.startsWith('### ')) {
      flushList();
      renderedElements.push(
        <h4 key={`h4-${i}`} className="text-sm font-bold text-navy mt-3 mb-1.5 flex items-center gap-1.5">
          {parseInlineMarkdown(trimmed.slice(4))}
        </h4>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      renderedElements.push(
        <h3 key={`h3-${i}`} className="text-base font-bold text-navy mt-3.5 mb-2 flex items-center gap-1.5">
          {parseInlineMarkdown(trimmed.slice(3))}
        </h3>
      );
      continue;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      renderedElements.push(
        <h2 key={`h2-${i}`} className="text-lg font-extrabold text-navy mt-4 mb-2.5">
          {parseInlineMarkdown(trimmed.slice(2))}
        </h2>
      );
      continue;
    }

    // Unordered List (- or *)
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (inList !== 'ul') {
        flushList();
        inList = 'ul';
      }
      listItems.push(
        <li key={`li-${i}`} className="text-sm leading-relaxed">
          {parseInlineMarkdown(trimmed.slice(2))}
        </li>
      );
      continue;
    }

    // Ordered List (1. 2. etc)
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      if (inList !== 'ol') {
        flushList();
        inList = 'ol';
      }
      listItems.push(
        <li key={`oli-${i}`} className="text-sm leading-relaxed">
          {parseInlineMarkdown(numMatch[2])}
        </li>
      );
      continue;
    }

    // Regular paragraph / blank line
    flushList();

    if (!trimmed) {
      renderedElements.push(<div key={`sp-${i}`} className="h-2" />);
    } else {
      renderedElements.push(
        <p key={`p-${i}`} className="text-sm leading-relaxed text-ink-light my-1">
          {parseInlineMarkdown(rawLine)}
        </p>
      );
    }
  }

  flushList();
  flushTable();

  return <div className={`space-y-1 ${className}`}>{renderedElements}</div>;
}
