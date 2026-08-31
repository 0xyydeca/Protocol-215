import { chromium } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(here, "../../../docs/evidence");

const pages = [
  "01-firestore-completed-run",
  "02-gcs-protocols-same-run",
  "03-pubsub-workflow",
  "04-cloud-run-services",
  "05-manifest",
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
for (const name of pages) {
  const html = path.join(evidenceDir, `${name}.html`);
  const png = path.join(evidenceDir, `${name}.png`);
  await page.goto(`file://${html}`);
  await page.screenshot({ path: png, fullPage: true });
  console.log("wrote", png);
}
await browser.close();
