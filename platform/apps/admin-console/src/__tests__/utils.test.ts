import { describe, it, expect } from "vitest";
import {
  normalizePhone,
  extractPhonesFromText,
  extractPhonesFromCsv,
  isValidEditionKey,
  parseWatiConversations,
} from "../lib/utils";

// ── normalizePhone ────────────────────────────────────────────────────────────

describe("normalizePhone", () => {
  it("strips + prefix", () => {
    expect(normalizePhone("+33612345678")).toBe("33612345678");
  });

  it("strips spaces and dashes", () => {
    expect(normalizePhone("06 12 34 56 78")).toBe("0612345678");
    expect(normalizePhone("06-12-34-56-78")).toBe("0612345678");
  });

  it("returns null for empty string", () => {
    expect(normalizePhone("")).toBeNull();
    expect(normalizePhone("   ")).toBeNull();
  });

  it("returns null for strings shorter than 8 digits", () => {
    expect(normalizePhone("1234567")).toBeNull();
    expect(normalizePhone("+123456")).toBeNull();
  });

  it("accepts exactly 8-digit numbers", () => {
    expect(normalizePhone("12345678")).toBe("12345678");
  });

  it("strips non-digit non-plus characters", () => {
    expect(normalizePhone("+229 01 020 304")).toBe("22901020304");
  });

  it("returns null for letters-only input", () => {
    expect(normalizePhone("abcdefgh")).toBeNull();
  });
});

// ── extractPhonesFromText ─────────────────────────────────────────────────────

describe("extractPhonesFromText", () => {
  it("splits on newline", () => {
    const result = extractPhonesFromText("+33612345678\n+33698765432");
    expect(result).toEqual(["33612345678", "33698765432"]);
  });

  it("splits on comma", () => {
    const result = extractPhonesFromText("+33612345678,+33698765432");
    expect(result).toEqual(["33612345678", "33698765432"]);
  });

  it("splits on semicolon, pipe and tab", () => {
    const result = extractPhonesFromText("+33600000001;+33600000002|+33600000003\t+33600000004");
    expect(result).toHaveLength(4);
  });

  it("deduplicates identical phones", () => {
    const result = extractPhonesFromText("+33612345678\n+33612345678\n33612345678");
    expect(result).toHaveLength(1);
    expect(result[0]).toBe("33612345678");
  });

  it("ignores tokens shorter than 8 digits", () => {
    const result = extractPhonesFromText("hello +33612345678 world");
    expect(result).toEqual(["33612345678"]);
  });

  it("returns empty array for blank input", () => {
    expect(extractPhonesFromText("")).toEqual([]);
    expect(extractPhonesFromText("   ")).toEqual([]);
  });
});

// ── extractPhonesFromCsv ──────────────────────────────────────────────────────

describe("extractPhonesFromCsv", () => {
  it("parses comma-separated CSV", () => {
    const csv = "name,phone\nAlice,33612345678\nBob,33698765432";
    const result = extractPhonesFromCsv(csv);
    expect(result).toContain("33612345678");
    expect(result).toContain("33698765432");
  });

  it("parses semicolon-separated CSV", () => {
    const csv = "name;phone\nAlice;33612345678";
    const result = extractPhonesFromCsv(csv);
    expect(result).toContain("33612345678");
  });

  it("deduplicates phones across rows", () => {
    const csv = "33612345678\n33612345678";
    const result = extractPhonesFromCsv(csv);
    expect(result).toHaveLength(1);
  });

  it("handles Windows-style CRLF line endings", () => {
    const csv = "33612345678\r\n33698765432\r\n";
    const result = extractPhonesFromCsv(csv);
    expect(result).toContain("33612345678");
    expect(result).toContain("33698765432");
  });
});

// ── isValidEditionKey ─────────────────────────────────────────────────────────

describe("isValidEditionKey", () => {
  it("accepts EU format", () => {
    expect(isValidEditionKey("2026-06-11-eu")).toBe(true);
  });

  it("accepts USCA format", () => {
    expect(isValidEditionKey("2026-06-11-usca")).toBe(true);
  });

  it("accepts US-CA format", () => {
    expect(isValidEditionKey("2026-06-11-us-ca")).toBe(true);
  });

  it("is case-insensitive for the region suffix", () => {
    expect(isValidEditionKey("2026-06-11-EU")).toBe(true);
    expect(isValidEditionKey("2026-06-11-USCA")).toBe(true);
  });

  it("rejects free-text edition names", () => {
    expect(isValidEditionKey("L'OPPORTUNITE AMAZON FBA")).toBe(false);
    expect(isValidEditionKey("challenge-amazon")).toBe(false);
  });

  it("rejects wrong separator", () => {
    expect(isValidEditionKey("2026/06/11-eu")).toBe(false);
  });

  it("rejects missing region", () => {
    expect(isValidEditionKey("2026-06-11")).toBe(false);
  });

  it("rejects unknown region", () => {
    expect(isValidEditionKey("2026-06-11-fr")).toBe(false);
  });

  it("trims surrounding whitespace before validating", () => {
    expect(isValidEditionKey("  2026-06-11-eu  ")).toBe(true);
  });
});

// ── parseWatiConversations ────────────────────────────────────────────────────

describe("parseWatiConversations", () => {
  it("returns zeros for empty/non-Wati CSV", () => {
    const result = parseWatiConversations("random,data\nwithout,wati,columns");
    expect(result.total_messages).toBe(0);
    expect(result.unique_contacts).toBe(0);
  });

  it("counts rows as messages when header matches", () => {
    const csv = "from,message,contact\n22901020304,Bonjour comment ca va ?,foo\n22901020305,Super merci beaucoup,bar";
    const result = parseWatiConversations(csv);
    expect(result.total_messages).toBe(2);
  });

  it("deduplicates unique contacts by phone", () => {
    const csv = "from,message,contact\n22901020304,Question sur le challenge ?,x\n22901020304,Autre message long enough,x";
    const result = parseWatiConversations(csv);
    expect(result.unique_contacts).toBe(1);
  });

  it("extracts top questions from rows with ? or long text", () => {
    const csv = "from,message,contact\n22901020304,Comment rejoindre le live ?,x";
    const result = parseWatiConversations(csv);
    expect(result.top_questions.length).toBeGreaterThan(0);
  });

  it("avg_response_time is N/A for empty input", () => {
    const result = parseWatiConversations("");
    expect(result.avg_response_time).toBe("N/A");
  });
});
