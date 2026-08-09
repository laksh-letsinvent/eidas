import { notFound } from "next/navigation";
import { MarkdownDoc } from "@/components/MarkdownDoc";
import { ESSAYS, getEssayContent, getEssayMeta } from "@/lib/essays";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return ESSAYS.map((essay) => ({ slug: essay.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const meta = getEssayMeta(slug);
  return { title: meta ? `${meta.title} — eIDAS Wallet & QES Lab` : "Essay — eIDAS Wallet & QES Lab" };
}

export default async function EssayPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const meta = getEssayMeta(slug);
  if (!meta) notFound();

  const content = getEssayContent(slug);
  return <MarkdownDoc eyebrow="Essay" content={content} />;
}
