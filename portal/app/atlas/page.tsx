import Markdown from "@/components/Markdown";
import { getAtlas } from "@/lib/content";

export const metadata = { title: "Atlas — eIDAS Wallet & QES Lab" };

export default function AtlasPage() {
  const md = getAtlas();
  return (
    <article>
      <div className="eyebrow">Atlas</div>
      <Markdown>{md}</Markdown>
    </article>
  );
}
