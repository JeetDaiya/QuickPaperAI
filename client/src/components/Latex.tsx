import { useMemo } from "react";
import katex from "katex";

// Matches the backend's own rendering convention exactly (html_paper_formatter.py's
// renderMathInElement delimiters): $$...$$ for display math, $...$ for inline math.
const MATH_SEGMENT = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;

interface Segment {
  text: string;
  isMath: boolean;
  display: boolean;
}

function splitSegments(text: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(MATH_SEGMENT)) {
    const index = match.index ?? 0;
    if (index > lastIndex) segments.push({ text: text.slice(lastIndex, index), isMath: false, display: false });
    const [full, display, inline] = match;
    segments.push({ text: display ?? inline ?? "", isMath: true, display: display !== undefined });
    lastIndex = index + full.length;
  }
  if (lastIndex < text.length) segments.push({ text: text.slice(lastIndex), isMath: false, display: false });
  return segments;
}

/** Renders question/answer text that may contain LaTeX math, using the same $$/$ delimiter
 * convention the backend's PDF/DOCX output uses — so on-screen review matches the compiled paper.
 *
 * Always renders as exactly one wrapping <span>, never a bare Fragment: a Fragment's children
 * become independent items when the parent uses flex/grid (each text run and math span gets
 * pulled out and laid out as its own box instead of flowing inline as one sentence) — wrapping
 * in a single element keeps that layout-agnostic regardless of what container it's dropped into. */
export function Latex({ text }: { text: string }) {
  const segments = useMemo(() => splitSegments(text), [text]);

  if (!segments.some((s) => s.isMath)) return <span>{text}</span>;

  return (
    <span>
      {segments.map((segment, i) => {
        if (!segment.isMath) return <span key={i}>{segment.text}</span>;
        const html = katex.renderToString(segment.text, {
          throwOnError: false,
          displayMode: segment.display,
          strict: "ignore",
        });
        // KaTeX's own displayMode output already carries a .katex-display class that applies
        // `display: block` via CSS — the wrapping tag itself can stay a <span> either way.
        return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
      })}
    </span>
  );
}
