// Pure geometry for the route map: no DOM and no MapLibre, so it runs under
// `node --test` (tests/js). Coordinates from the backend are [lat, lon];
// toLngLat is the one place they become GeoJSON's [lon, lat].

const METRES_PER_DEGREE = 111320;

// A vehicle further than this from every stop is not on this pattern at all.
export const NEAREST_STOP_MAX_M = 2000;
// Further than this from the drawn line, the vehicle has left it (a detour, a
// depot run), and splitting the line at the nearest point would be a guess.
export const OFF_ROUTE_M = 200;
// How far either side of the vehicle's stop the split may be looked for. Wide
// enough to cover the gap between two stops, narrow enough that a line which
// comes back along the same street cannot be split on its way back.
const SEARCH_WINDOW_M = 1500;
// A fall of more than this many stops is a new run, not GPS noise.
const NEW_RUN_STOPS = 3;

const AHEAD_STOPS = 6;
const MAX_AHEAD_STOPS = 12;

export const toLngLat = ([lat, lon]) => [lon, lat];

export const isPoint = (point) =>
  Array.isArray(point) &&
  Number.isFinite(point[0]) &&
  Number.isFinite(point[1]) &&
  !(point[0] === 0 && point[1] === 0);

export const stopPoint = (stop) =>
  stop && stop.lat != null && stop.lon != null ? [Number(stop.lat), Number(stop.lon)] : null;

/** Metres between two [lat, lon] points, in a local flat projection. */
export const distanceM = (a, b) => {
  const cos = Math.cos((((a[0] + b[0]) / 2) * Math.PI) / 180);
  const dy = (b[0] - a[0]) * METRES_PER_DEGREE;
  const dx = (b[1] - a[1]) * METRES_PER_DEGREE * cos;
  return Math.hypot(dx, dy);
};

/** A line with the distance along it at each of its points. */
export const measureLine = (points) => {
  const clean = (points || []).filter(isPoint);
  const along = [0];
  for (let i = 1; i < clean.length; i++) {
    along.push(along[i - 1] + distanceM(clean[i - 1], clean[i]));
  }
  return { points: clean, along, length: along[along.length - 1] ?? 0 };
};

// Two candidates this close in distance from the line are the same street
// (both directions of it); the one nearer the expected place wins.
const SAME_STREET_M = 15;

/**
 * The point on a line nearest to `point`, searched between `from` and `to`
 * metres along it. Where the line passes the point twice -- out and back along
 * one street -- the pass nearest `near` metres along wins. Returns the
 * distance along the line and how far off it the point is, or null.
 */
export const locateOnLine = (line, point, from = 0, to = Infinity, near = from) => {
  const { points, along } = line;
  if (points.length < 2 || !isPoint(point)) return null;
  const cos = Math.cos((point[0] * Math.PI) / 180);
  const px = point[1] * cos;
  const py = point[0];
  let best = null;
  for (let i = 1; i < points.length; i++) {
    if (along[i] < from || along[i - 1] > to) continue;
    const ax = points[i - 1][1] * cos;
    const ay = points[i - 1][0];
    const dx = points[i][1] * cos - ax;
    const dy = points[i][0] - ay;
    const lengthSq = dx * dx + dy * dy;
    // A segment of no length (a repeated point) has only its start to offer.
    const t =
      lengthSq === 0
        ? 0
        : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSq));
    const off = Math.hypot(px - ax - t * dx, py - ay - t * dy) * METRES_PER_DEGREE;
    const at = Math.max(from, Math.min(to, along[i - 1] + t * (along[i] - along[i - 1])));
    const better =
      !best ||
      (Math.abs(off - best.off) <= SAME_STREET_M
        ? Math.abs(at - near) < Math.abs(best.along - near)
        : off < best.off);
    if (better) best = { off, along: at };
  }
  return best;
};

/** The point `metres` along a line. */
export const pointAt = (line, metres) => {
  const { points, along } = line;
  if (!points.length) return null;
  if (metres <= 0) return points[0];
  for (let i = 1; i < points.length; i++) {
    if (along[i] >= metres) {
      const span = along[i] - along[i - 1];
      const t = span ? (metres - along[i - 1]) / span : 0;
      return [
        points[i - 1][0] + t * (points[i][0] - points[i - 1][0]),
        points[i - 1][1] + t * (points[i][1] - points[i - 1][1]),
      ];
    }
  }
  return points[points.length - 1];
};

/** The line cut in two at `metres`, both halves sharing the cut point. */
export const splitLine = (line, metres) => {
  const { points, along } = line;
  if (points.length < 2) return { done: [], ahead: points };
  const cut = pointAt(line, metres);
  const done = points.filter((_, i) => along[i] < metres);
  const ahead = points.filter((_, i) => along[i] > metres);
  return { done: [...done, cut], ahead: [cut, ...ahead] };
};

/**
 * How far along the line each stop is. Each stop is looked for only beyond the
 * one before it, which is what keeps a line that returns along its own street
 * from placing a later stop on the outbound leg.
 */
export const stopPositions = (line, stops) => {
  let from = 0;
  return stops.map((stop) => {
    const point = stopPoint(stop);
    const found = point ? locateOnLine(line, point, from) : null;
    if (!found) return null;
    from = found.along;
    return found.along;
  });
};

/** Which stop the vehicle is at, or -1 when it is nowhere near the pattern. */
export const nearestStopIndex = (stops, vehicle) => {
  if (!isPoint(vehicle)) return -1;
  let best = -1;
  let bestDistance = Infinity;
  stops.forEach((stop, index) => {
    const point = stopPoint(stop);
    if (!point) return;
    const metres = distanceM(vehicle, point);
    if (metres < bestDistance) {
      bestDistance = metres;
      best = index;
    }
  });
  return bestDistance <= NEAREST_STOP_MAX_M ? best : -1;
};

/**
 * Where to split the line at the vehicle, or null to draw it whole.
 *
 * The search is held to a window around the vehicle's stop, so a loop or a
 * line that comes back the same way cannot be split on the wrong leg.
 */
export const vehicleSplit = (line, positions, hereIndex, vehicle) => {
  if (line.points.length < 2 || !isPoint(vehicle)) return null;
  const centre = hereIndex >= 0 ? positions[hereIndex] : null;
  let found;
  if (centre == null) {
    found = locateOnLine(line, vehicle);
  } else {
    // Between the stops either side of the one it is at, and never further
    // than the window: that is where a vehicle at this stop can be.
    const before = positions.slice(0, hereIndex).filter((p) => p != null).at(-1);
    const after = positions.slice(hereIndex + 1).find((p) => p != null);
    const from = Math.max(before ?? 0, centre - SEARCH_WINDOW_M);
    const to = Math.min(after ?? Infinity, centre + SEARCH_WINDOW_M);
    found = locateOnLine(line, vehicle, from, to, centre);
  }
  if (!found || found.off > OFF_ROUTE_M) return null;
  return found.along;
};

/**
 * Progress along a run that only moves forward.
 *
 * GPS jitter can put a stopped bus a few metres behind where it was; drawing
 * the travelled part shrinking and growing again looks broken. A new vehicle,
 * or a fall of several stops (the same vehicle starting its next run), starts
 * over.
 */
export const createProgress = () => {
  let key = null;
  let best = null;
  let bestStop = -1;
  return {
    update(nextKey, stopIndex, metres) {
      if (nextKey !== key || (bestStop >= 0 && stopIndex >= 0 && stopIndex < bestStop - NEW_RUN_STOPS)) {
        key = nextKey;
        best = null;
        bestStop = -1;
      }
      if (metres == null) return best;
      if (best == null || metres > best) best = metres;
      if (stopIndex > bestStop) bestStop = stopIndex;
      return best;
    },
    reset() {
      key = null;
      best = null;
      bestStop = -1;
    },
  };
};

/**
 * The points the map should frame.
 *
 * The stretch a rider cares about runs from the vehicle to their own stop;
 * fitting a whole intercity route would put both inside a few pixels.
 */
export const focusPoints = ({ stops, vehicle, hereIndex, mineIndex }) => {
  const all = stops.map(stopPoint).filter(isPoint);
  const mine = mineIndex >= 0 ? stopPoint(stops[mineIndex]) : null;
  if (!isPoint(vehicle)) {
    // No vehicle: the whole route, which is what the rider is about to take.
    return all;
  }
  if (hereIndex < 0) return [vehicle, ...(mine ? [mine] : all)];
  const last =
    mineIndex > hereIndex
      ? Math.min(mineIndex, hereIndex + MAX_AHEAD_STOPS)
      : hereIndex + AHEAD_STOPS;
  const stretch = stops
    .slice(hereIndex, last + 1)
    .map(stopPoint)
    .filter(isPoint);
  return [vehicle, ...(stretch.length ? stretch : all)];
};

/** [[west, south], [east, north]] around [lat, lon] points, or null. */
export const boundsOf = (points) => {
  const valid = (points || []).filter(isPoint);
  if (!valid.length) return null;
  let south = Infinity;
  let north = -Infinity;
  let west = Infinity;
  let east = -Infinity;
  for (const [lat, lon] of valid) {
    south = Math.min(south, lat);
    north = Math.max(north, lat);
    west = Math.min(west, lon);
    east = Math.max(east, lon);
  }
  return [
    [west, south],
    [east, north],
  ];
};

/**
 * Seconds since a position was recorded, on the server's clock.
 *
 * `offset` is server time minus this device's time when the answer arrived, so
 * a phone whose clock is minutes off still ages a position correctly, and the
 * age keeps growing when answers stop coming.
 */
export const positionAge = (seen, offset, now = Date.now()) => {
  const recorded = Date.parse(seen);
  if (Number.isNaN(recorded)) return null;
  return Math.max(0, Math.round((now + offset - recorded) / 1000));
};

/** Server time minus device time, from one answer; 0 when unknown. */
export const clockOffset = (serverTime, receivedAt) => {
  const server = Date.parse(serverTime);
  return Number.isNaN(server) ? 0 : server - receivedAt;
};

/**
 * Turns CSS colours into ones MapLibre can parse.
 *
 * Themes may set colours MapLibre cannot read (color-mix(), oklch(),
 * light-dark()); `toRgb` is where the browser resolves them, and anything it
 * cannot resolve falls back rather than breaking a layer.
 */
export const createColorResolver = (toRgb) => {
  const cache = new Map();
  return (value, fallback) => {
    const key = `${value}|${fallback}`;
    if (cache.has(key)) return cache.get(key);
    let resolved = null;
    if (value && String(value).trim()) {
      try {
        resolved = toRgb(String(value).trim());
      } catch {
        resolved = null;
      }
    }
    const result = resolved || fallback;
    cache.set(key, result);
    return result;
  };
};
