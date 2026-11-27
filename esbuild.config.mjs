// Bundles the card into the integration's www/ directory, which the component
// serves and registers as a Lovelace resource.
//
// Lit is bundled rather than borrowed from the Home Assistant frontend at
// runtime: reaching into HA's internals for it has broken repeatedly across
// releases, and a CDN import would break offline installs.
//
// MapLibre is not bundled. Version 6 is an ES module that starts its worker
// from a file beside itself, so it is copied as published into a folder named
// after its version: an upgrade then replaces every file of it at once, and no
// browser keeps a stale worker next to a new main script.
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";

import { build, context } from "esbuild";

// One version for the integration and its card: the manifest's.
const { version } = JSON.parse(
  readFileSync("custom_components/israel_transit/manifest.json", "utf8"),
);
const { version: maplibreVersion } = JSON.parse(
  readFileSync("node_modules/maplibre-gl/package.json", "utf8"),
);

const WWW = "custom_components/israel_transit/www";
const VENDOR = `${WWW}/vendor`;
const MAPLIBRE_DIR = `maplibre-${maplibreVersion}`;

/** Copy MapLibre into www/vendor, dropping any older version beside it. */
const vendorMaplibre = () => {
  mkdirSync(VENDOR, { recursive: true });
  for (const entry of readdirSync(VENDOR)) {
    if (entry.startsWith("maplibre-") && entry !== MAPLIBRE_DIR) {
      rmSync(`${VENDOR}/${entry}`, { recursive: true, force: true });
    }
  }
  const target = `${VENDOR}/${MAPLIBRE_DIR}`;
  mkdirSync(target, { recursive: true });
  const source = "node_modules/maplibre-gl";
  for (const file of ["maplibre-gl.mjs", "maplibre-gl-worker.mjs", "maplibre-gl.css"]) {
    // The source maps are not shipped, so the comments pointing at them would
    // only fill the browser console with 404s.
    const text = readFileSync(`${source}/dist/${file}`, "utf8").replace(
      /\n\/\/# sourceMappingURL=\S+\s*$/,
      "\n",
    );
    writeFileSync(`${target}/${file}`, text);
  }
  // BSD-3 asks for the notice to travel with the code.
  writeFileSync(`${target}/LICENSE.txt`, readFileSync(`${source}/LICENSE.txt`));
};

const options = {
  entryPoints: ["src/index.js"],
  outfile: `${WWW}/israel-transit-card.js`,
  bundle: true,
  minify: true,
  sourcemap: false,
  format: "esm",
  target: "es2021",
  legalComments: "none",
  define: {
    __CARD_VERSION__: JSON.stringify(version),
    __MAPLIBRE_DIR__: JSON.stringify(MAPLIBRE_DIR),
  },
  banner: { js: "/* Israel Transit card - https://github.com/yosef-chai/israel-transit */" },
};

vendorMaplibre();

if (process.argv.includes("--watch")) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("watching...");
} else {
  await build(options);
  console.log("built", options.outfile, "and", `${VENDOR}/${MAPLIBRE_DIR}`);
}
