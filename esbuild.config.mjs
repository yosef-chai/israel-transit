// Bundles the card into the integration's www/ directory, which the component
// serves and registers as a Lovelace resource.
//
// Lit is bundled rather than borrowed from the Home Assistant frontend at
// runtime: reaching into HA's internals for it has broken repeatedly across
// releases, and a CDN import would break offline installs.
import { readFileSync } from "node:fs";

import { build, context } from "esbuild";

// One version for the integration and its card: the manifest's.
const { version } = JSON.parse(
  readFileSync("custom_components/israel_transit/manifest.json", "utf8"),
);

const options = {
  entryPoints: ["src/index.js"],
  outfile: "custom_components/israel_transit/www/israel-transit-card.js",
  bundle: true,
  minify: true,
  sourcemap: false,
  format: "esm",
  target: "es2021",
  legalComments: "none",
  define: { __CARD_VERSION__: JSON.stringify(version) },
  banner: { js: "/* Israel Transit card - https://github.com/yosef-chai/israel-transit */" },
};

if (process.argv.includes("--watch")) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("watching...");
} else {
  await build(options);
  console.log("built", options.outfile);
}
