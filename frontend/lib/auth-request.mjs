export async function readBoundedJson(request, maxBytes = 4096) {
  const declaredHeader = request.headers.get("content-length");
  if (declaredHeader !== null) {
    if (!/^\d+$/.test(declaredHeader)) return { ok: false, status: 400, detail: "invalid_json" };
    if (Number(declaredHeader) > maxBytes) return { ok: false, status: 413, detail: "request_body_too_large" };
  }
  if (!request.body) return { ok: false, status: 400, detail: "invalid_json" };

  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel().catch(() => undefined);
        return { ok: false, status: 413, detail: "request_body_too_large" };
      }
      chunks.push(value);
    }
  } catch {
    return { ok: false, status: 400, detail: "invalid_json" };
  } finally {
    try { reader.releaseLock(); } catch { /* already cancelled */ }
  }

  try {
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    const value = JSON.parse(decoded);
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { ok: false, status: 400, detail: "json_object_required" };
    }
    return { ok: true, value };
  } catch {
    return { ok: false, status: 400, detail: "invalid_json" };
  }
}
