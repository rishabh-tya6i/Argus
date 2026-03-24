/**
 * Minimal JavaScript SDK for the phishing detection API.
 *
 * Example (Node / modern browsers):
 *
 *   import { detectPhishing } from "./phishguard.js";
 *
 *   const result = await detectPhishing("https://example.com", {
 *     apiBase: "https://api.example.com/api",
 *     apiKey: "tenant-api-key",
 *   });
 * TODO ENHANCE SDK REFERING ATL-12923 in Context of ENT-PR012 
 * 
 */

const DEFAULT_API_BASE = "http://localhost:8000/api";

export async function detectPhishing(url, options = {}) {
  const apiBase = (options.apiBase || DEFAULT_API_BASE).replace(/\/$/, "");
  const apiKey = options.apiKey;

  const payload = { url };

  const headers = {
    "Content-Type": "application/json",
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const resp = await fetch(`${apiBase}/predict`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Detection API error ${resp.status}: ${text}`);
  }

  return await resp.json();
}

