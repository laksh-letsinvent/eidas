import { MarkdownDoc } from "@/components/MarkdownDoc";
import { getAtlas } from "@/lib/experiment";

export const dynamic = "force-static";
export const metadata = { title: "Atlas — eIDAS Wallet & QES Lab" };

export default function AtlasPage() {
  return <MarkdownDoc eyebrow="Atlas" content={getAtlas()} />;
}
