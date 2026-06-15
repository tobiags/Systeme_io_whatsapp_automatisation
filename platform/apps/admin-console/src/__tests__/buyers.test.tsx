import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";

// ── Inline minimal BuyersTab logic ────────────────────────────────────────────
// We test the fetch logic and result rendering without importing the full
// StreamyardOpsPage (which depends on many context + env vars).

import { extractPhonesFromText } from "../lib/utils";

// Reproduce the core fetch logic as a pure function so we can unit-test it.
const API_BASE = "http://localhost:8000";

type BuyerStatus = "converted" | "already" | "not_found" | "error";
type BuyerResult = { phone: string; status: BuyerStatus; contact_id?: string; detail?: string };

async function markBuyersLogic(
  phones: string[],
  fetchFn: typeof fetch,
): Promise<BuyerResult[]> {
  const out: BuyerResult[] = [];
  for (const phone of phones) {
    try {
      const res = await fetchFn(`${API_BASE}/webhooks/systemeio/purchase`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        out.push({ phone, status: "error", detail: data.detail || `HTTP ${res.status}` });
      } else if (data.status === "ignored") {
        out.push({ phone, status: "not_found", detail: data.reason });
      } else if (data.status === "already_converted") {
        out.push({ phone, status: "already", contact_id: data.contact_id });
      } else {
        out.push({ phone, status: "converted", contact_id: data.contact_id });
      }
    } catch {
      out.push({ phone, status: "error", detail: "Erreur réseau" });
    }
  }
  return out;
}

// ── extractPhonesFromText integration ─────────────────────────────────────────

describe("phone extraction before marking", () => {
  it("parses +prefix phones correctly", () => {
    const list = extractPhonesFromText("+22997551273\n+4917674706763");
    expect(list).toEqual(["22997551273", "4917674706763"]);
  });

  it("deduplicates identical phones", () => {
    const list = extractPhonesFromText("+22997551273\n22997551273\n+22997551273");
    expect(list).toHaveLength(1);
  });

  it("ignores blank lines", () => {
    const list = extractPhonesFromText("\n\n+22997551273\n\n");
    expect(list).toEqual(["22997551273"]);
  });
});

// ── markBuyersLogic ───────────────────────────────────────────────────────────

describe("markBuyersLogic — converted", () => {
  it("returns converted when API responds with status=converted", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "converted", contact_id: "ct_abc123", event_type: "paid_offer" }),
    });
    const results = await markBuyersLogic(["22997551273"], mockFetch as unknown as typeof fetch);
    expect(results).toHaveLength(1);
    expect(results[0].status).toBe("converted");
    expect(results[0].contact_id).toBe("ct_abc123");
  });

  it("sends the phone without + prefix in the body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "converted", contact_id: "ct_abc123" }),
    });
    await markBuyersLogic(["22997551273"], mockFetch as unknown as typeof fetch);
    const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
    expect(body.phone).toBe("22997551273");
  });

  it("calls the correct endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "converted", contact_id: "ct_abc123" }),
    });
    await markBuyersLogic(["22997551273"], mockFetch as unknown as typeof fetch);
    expect(mockFetch.mock.calls[0][0]).toContain("/webhooks/systemeio/purchase");
  });
});

describe("markBuyersLogic — already_converted", () => {
  it("returns already when API responds with already_converted", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "already_converted", contact_id: "ct_xyz" }),
    });
    const results = await markBuyersLogic(["22997551273"], mockFetch as unknown as typeof fetch);
    expect(results[0].status).toBe("already");
    expect(results[0].contact_id).toBe("ct_xyz");
  });
});

describe("markBuyersLogic — not_found", () => {
  it("returns not_found when API responds with status=ignored", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ignored", reason: "contact_not_found" }),
    });
    const results = await markBuyersLogic(["33600000000"], mockFetch as unknown as typeof fetch);
    expect(results[0].status).toBe("not_found");
    expect(results[0].detail).toBe("contact_not_found");
  });
});

describe("markBuyersLogic — error cases", () => {
  it("returns error on non-ok HTTP response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Internal server error" }),
    });
    const results = await markBuyersLogic(["33600000000"], mockFetch as unknown as typeof fetch);
    expect(results[0].status).toBe("error");
    expect(results[0].detail).toBe("Internal server error");
  });

  it("returns error on network failure", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error("Network failure"));
    const results = await markBuyersLogic(["33600000000"], mockFetch as unknown as typeof fetch);
    expect(results[0].status).toBe("error");
    expect(results[0].detail).toBe("Erreur réseau");
  });

  it("falls back to HTTP status when detail is missing", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({}),
    });
    const results = await markBuyersLogic(["33600000000"], mockFetch as unknown as typeof fetch);
    expect(results[0].detail).toBe("HTTP 503");
  });
});

describe("markBuyersLogic — batch processing", () => {
  it("processes multiple phones and returns one result per phone", async () => {
    const phones = ["22997551273", "4917674706763", "33600000000"];
    let callCount = 0;
    const mockFetch = vi.fn().mockImplementation(async () => {
      callCount++;
      return {
        ok: true,
        json: async () => ({ status: "converted", contact_id: `ct_${callCount}` }),
      };
    });
    const results = await markBuyersLogic(phones, mockFetch as unknown as typeof fetch);
    expect(results).toHaveLength(3);
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("continues after a single phone error", async () => {
    const phones = ["22997551273", "bad", "4917674706763"];
    let call = 0;
    const mockFetch = vi.fn().mockImplementation(async () => {
      call++;
      if (call === 2) throw new Error("fail");
      return { ok: true, json: async () => ({ status: "converted", contact_id: "ct_ok" }) };
    });
    const results = await markBuyersLogic(phones, mockFetch as unknown as typeof fetch);
    expect(results[0].status).toBe("converted");
    expect(results[1].status).toBe("error");
    expect(results[2].status).toBe("converted");
  });

  it("counts converted/not_found correctly across a mixed batch", async () => {
    const responses = [
      { ok: true, json: async () => ({ status: "converted", contact_id: "ct_1" }) },
      { ok: true, json: async () => ({ status: "ignored", reason: "contact_not_found" }) },
      { ok: true, json: async () => ({ status: "already_converted", contact_id: "ct_3" }) },
    ];
    let i = 0;
    const mockFetch = vi.fn().mockImplementation(async () => responses[i++]);
    const results = await markBuyersLogic(
      ["11111111111", "22222222222", "33333333333"],
      mockFetch as unknown as typeof fetch,
    );
    expect(results.filter((r) => r.status === "converted")).toHaveLength(1);
    expect(results.filter((r) => r.status === "not_found")).toHaveLength(1);
    expect(results.filter((r) => r.status === "already")).toHaveLength(1);
  });
});
