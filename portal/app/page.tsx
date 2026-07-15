import { MarkdownDoc } from "@/components/MarkdownDoc";
import { getExperiment } from "@/lib/experiment";

export const dynamic = "force-static";

export default function Home() {
  return <MarkdownDoc eyebrow="The Experiment" content={getExperiment()} />;
}
