import { readFileSync } from "fs";
import path from "path";

/**
 * Public cut of the Experiment brief.
 * Single source file; drops the internal tail (open questions, next actions,
 * metadata footer) and strips [ASSUMED — confirm] tags so the page is safe
 * to publish without a second copy.
 */
export function getExperiment(): string {
  const raw = readFileSync(
    path.join(process.cwd(), "content", "WALLET-QES-LAB-BRIEF.md"),
    "utf-8"
  );
  const lines = raw.split("\n");
  const cut = [/^##\s+Open questions/i, /^##\s+Next actions/i];
  let cutAt = lines.length;
  for (let i = 0; i < lines.length; i++) {
    if (cut.some((re) => re.test(lines[i]))) {
      cutAt = i;
      break;
    }
  }
  let body = lines.slice(0, cutAt).join("\n");
  body = body.replace(/\n+---\s*$/g, "\n");
  body = body.replace(/\s*\[ASSUMED[^\]]*\]/g, "");
  return body.trimEnd() + "\n";
}

export function getAtlas(): string {
  return readFileSync(
    path.join(process.cwd(), "content", "ATLAS_EUDI.md"),
    "utf-8"
  );
}
