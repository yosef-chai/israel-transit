// node --test tests/js
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  boundsOf,
  clockOffset,
  createColorResolver,
  createProgress,
  distanceM,
  focusPoints,
  measureLine,
  nearestStopIndex,
  positionAge,
  splitLine,
  stopPositions,
  toLngLat,
  vehicleProgress,
  vehicleSplit,
} from "../../src/map-geometry.js";

// About 111 m per 0.001° of latitude; a straight line north along lon 34.78.
const north = (steps) =>
  Array.from({ length: steps + 1 }, (_, i) => [32 + i * 0.001, 34.78]);

const stop = (lat, lon) => ({ lat, lon });

test("the server's [lat, lon] becomes GeoJSON's [lon, lat]", () => {
  assert.deepEqual(toLngLat([32.07, 34.79]), [34.79, 32.07]);
});

test("east-west distance shrinks with latitude", () => {
  const ns = distanceM([32, 34.78], [32.01, 34.78]);
  const ew = distanceM([32, 34.78], [32, 34.79]);
  // cos(32°) ≈ 0.848: ignoring it overstates east-west distances by 15%.
  assert.ok(Math.abs(ew / ns - Math.cos((32 * Math.PI) / 180)) < 0.001);
});

test("a line is split at the vehicle, both halves sharing the cut", () => {
  const line = measureLine(north(10));
  const at = vehicleSplit(line, [], -1, [32.0045, 34.78]);
  assert.ok(Math.abs(at - 500) < 2);
  const { done, ahead } = splitLine(line, at);
  assert.deepEqual(done.at(-1), ahead[0]);
  assert.ok(done.length + ahead.length >= line.points.length);
});

test("a vehicle far off the line leaves it whole", () => {
  const line = measureLine(north(10));
  // About 470 m east of the line.
  assert.equal(vehicleSplit(line, [], -1, [32.005, 34.785]), null);
});

test("a vehicle off the line but near a stop has got as far as that stop", () => {
  const line = measureLine(north(10));
  const stops = [stop(32, 34.78), stop(32.005, 34.78), stop(32.01, 34.78)];
  const positions = stopPositions(line, stops);
  // About 470 m east of the second stop: a detour, not on the drawn line.
  const detour = [32.005, 34.785];
  assert.equal(vehicleSplit(line, positions, 1, detour), null);
  assert.ok(Math.abs(vehicleProgress(line, positions, 1, detour) - positions[1]) < 1);
  // Nowhere near any stop: unknown.
  assert.equal(vehicleProgress(line, positions, -1, [31, 34]), null);
});

test("a line that returns along its own street is split on the right leg", () => {
  // Out north for 1.1 km, then back south along the same street.
  const out = north(10);
  const back = [...out].reverse().slice(1);
  const line = measureLine([...out, ...back]);
  const stops = [stop(32, 34.78), stop(32.005, 34.78), stop(32.01, 34.78), stop(32.005, 34.78), stop(32, 34.78)];
  const positions = stopPositions(line, stops);
  // The fourth stop sits on the way back, after the turn.
  assert.ok(positions[3] > line.length / 2);
  // The vehicle is at the fourth stop, so the split belongs on the way back too.
  const at = vehicleSplit(line, positions, 3, [32.005, 34.78]);
  assert.ok(at > line.length / 2, `split at ${at} of ${line.length}`);
});

test("a closed loop is measured and split without breaking", () => {
  const loop = measureLine([
    [32, 34.78],
    [32.005, 34.78],
    [32.005, 34.786],
    [32, 34.786],
    [32, 34.78],
  ]);
  assert.ok(loop.length > 0);
  const at = vehicleSplit(loop, [], -1, [32.005, 34.783]);
  assert.ok(at > 0 && at < loop.length);
});

test("progress only moves forward within one run", () => {
  const progress = createProgress();
  assert.equal(progress.update("36|bus1", 2, 500), 500);
  // GPS jitter a few metres back keeps the furthest point.
  assert.equal(progress.update("36|bus1", 2, 480), 500);
  assert.equal(progress.update("36|bus1", 3, 700), 700);
});

test("a new vehicle or a new run starts progress over", () => {
  const progress = createProgress();
  progress.update("36|bus1", 8, 4000);
  assert.equal(progress.update("36|bus2", 1, 100), 100);
  progress.update("36|bus2", 9, 4500);
  // The same bus back at the second stop is its next run.
  assert.equal(progress.update("36|bus2", 1, 120), 120);
});

test("the nearest stop is -1 when the vehicle is nowhere near", () => {
  const stops = [stop(32, 34.78), stop(32.01, 34.78)];
  assert.equal(nearestStopIndex(stops, [32.0098, 34.7801]), 1);
  assert.equal(nearestStopIndex(stops, [31.5, 34.78]), -1);
  assert.equal(nearestStopIndex(stops, null), -1);
});

test("framing follows the vehicle to the rider's stop", () => {
  const stops = north(20).map(([lat, lon]) => stop(lat, lon));
  const vehicle = [32.002, 34.78];
  const points = focusPoints({ stops, vehicle, hereIndex: 2, mineIndex: 5 });
  assert.deepEqual(points[0], vehicle);
  assert.equal(points.length, 1 + 4); // the vehicle, then stops 2 to 5
});

test("framing without a vehicle shows the whole route", () => {
  const stops = north(4).map(([lat, lon]) => stop(lat, lon));
  assert.equal(focusPoints({ stops, vehicle: null, hereIndex: -1, mineIndex: 2 }).length, 5);
});

test("a vehicle far from the route is framed with the rider's stop", () => {
  const stops = north(4).map(([lat, lon]) => stop(lat, lon));
  const far = [31.9, 34.7];
  const points = focusPoints({ stops, vehicle: far, hereIndex: -1, mineIndex: 2 });
  assert.deepEqual(points, [far, [32.002, 34.78]]);
});

test("bounds ignore unusable points", () => {
  assert.deepEqual(boundsOf([[32, 34.7], [0, 0], [32.1, 34.8], null]), [
    [34.7, 32],
    [34.8, 32.1],
  ]);
  assert.equal(boundsOf([]), null);
});

test("a position ages on the server's clock and keeps ageing", () => {
  const seen = "2026-11-27T10:00:00Z";
  // The phone runs five minutes slow.
  const received = Date.parse("2026-11-27T09:55:30Z");
  const offset = clockOffset("2026-11-27T10:00:30Z", received);
  assert.equal(positionAge(seen, offset, received), 30);
  // Two minutes later, with no new answer, it is two minutes older.
  assert.equal(positionAge(seen, offset, received + 120000), 150);
  assert.equal(positionAge("not a time", 0), null);
  assert.equal(clockOffset(undefined, received), 0);
});

test("colours fall back when the browser cannot resolve them, and are cached", () => {
  let calls = 0;
  const resolve = createColorResolver((value) => {
    calls += 1;
    if (value === "oops") throw new Error("bad");
    return value.startsWith("#") ? "rgb(1, 2, 3)" : null;
  });
  assert.equal(resolve("#010203", "black"), "rgb(1, 2, 3)");
  assert.equal(resolve("#010203", "black"), "rgb(1, 2, 3)");
  assert.equal(calls, 1);
  assert.equal(resolve("oops", "black"), "black");
  assert.equal(resolve("", "black"), "black");
  assert.equal(resolve("color-mix(in srgb, red, blue)", "black"), "black");
});
