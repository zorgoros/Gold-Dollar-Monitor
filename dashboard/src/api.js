const HISTORY_METRICS = ["usd_market", "usd_gold_implied", "usd_aed_implied"];

async function readJson(response) {
  if (!response.ok) throw new Error("dashboard unavailable");
  return response.json();
}

export async function getLatest(signal) {
  return readJson(await fetch("/api/v1/latest", { signal }));
}

export async function getHistory(range, signal) {
  const metrics = HISTORY_METRICS.join(",");
  return readJson(
    await fetch(`/api/v1/history?metrics=${metrics}&range=${range}`, { signal }),
  );
}
