// frontend/src/lib/api.js
const API_BASE = "/api";

export async function getJSON(path, params = {}) {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  });
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`GET ${path} ${res.status}`);
  return res.json();
}
