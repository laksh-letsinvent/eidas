import Markdown from "@/components/Markdown";
import { getExperiment } from "@/lib/content";

export default function Home() {
  const md = getExperiment();
  return (
    <article>
      <div className="eyebrow">The Experiment</div>
      <Markdown>{md}</Markdown>
    </article>
  );
}
