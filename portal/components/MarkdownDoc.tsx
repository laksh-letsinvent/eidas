"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

export function MarkdownDoc({
  eyebrow,
  content,
}: {
  eyebrow?: string;
  content: string;
}) {
  return (
    <div className="px-6 py-10 lg:px-12 lg:py-12 max-w-5xl">
      {eyebrow && (
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-c)]">
          {eyebrow}
        </div>
      )}
      <div className="prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
