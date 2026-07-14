import fs from "node:fs";
import path from "node:path";

const CONTENT_DIR = path.join(process.cwd(), "content");

function read(file: string): string {
  return fs.readFileSync(path.join(CONTENT_DIR, file), "utf8");
}

// Atlas renders verbatim.
export function getAtlas(): string {
  return read("ATLAS_EUDI.md");
}

/**
 * Public cut of the Experiment brief.
 * Single source file; we drop the internal tail (open questions, next actions,
 * the metadata footer) and strip [ASSUMED — confirm] tags so the page is safe
 * to publish without maintaining a second copy.
 */
export function getExperiment(): string {
  const raw = read("WALLET-QES-LAB-BRIEF.md");
  const lines = raw.split("\n");

  const cutHeadings = [/^##\s+Open questions/i, /^##\s+Next actions/i];
  let cutAt = lines.length;
  for (let i = 0; i < lines.length; i++) {
    if (cutHeadings.some((re) => re.test(lines[i]))) {
      cutAt = i;
      break;
    }
  }

  let body = lines.slice(0, cutAt).join("\n");

  // Drop any trailing horizontal rule left dangling by the cut.
  body = body.replace(/\n+---\s*$/g, "\n");

  // Strip inline planning tags.
  body = body.replace(/\s*\[ASSUMED[^\]]*\]/g, "");

  return body.trimEnd() + "\n";
}
