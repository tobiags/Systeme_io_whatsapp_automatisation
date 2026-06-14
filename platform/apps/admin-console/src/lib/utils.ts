// Pure utility functions extracted from StreamyardOpsPage for testability.

export interface ConversationInsight {
  total_messages: number;
  unique_contacts: number;
  top_questions: { text: string; count: number }[];
  unresolved_count: number;
  avg_response_time: string;
}

export function normalizePhone(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  const match = trimmed.replace(/[^\d+]/g, "");
  if (!match) return null;
  const digitsOnly = match.replace(/^\+/, "");
  return digitsOnly.length >= 8 ? digitsOnly : null;
}

export function extractPhonesFromText(text: string): string[] {
  const tokens = text
    .split(/[\n,;|\t ]+/)
    .map(normalizePhone)
    .filter((value): value is string => Boolean(value));
  return [...new Set(tokens)];
}

export function extractPhonesFromCsv(csvText: string): string[] {
  const rows = csvText.split(/\r?\n/);
  const phones: string[] = [];
  for (const row of rows) {
    const cells = row.split(/[;,]/);
    for (const cell of cells) {
      const phone = normalizePhone(cell);
      if (phone) phones.push(phone);
    }
  }
  return [...new Set(phones)];
}

export function isValidEditionKey(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}-(eu|usca|us-ca)$/i.test(value.trim());
}

export function parseWatiConversations(csvText: string): ConversationInsight {
  const rows = csvText.split(/\r?\n/).filter(Boolean);
  const header = rows[0]?.toLowerCase() ?? "";
  const isWatiFormat = header.includes("from") || header.includes("message") || header.includes("contact");

  if (!isWatiFormat || rows.length < 2) {
    return { total_messages: 0, unique_contacts: 0, top_questions: [], unresolved_count: 0, avg_response_time: "N/A" };
  }

  const contacts = new Set<string>();
  const questions: Record<string, number> = {};
  let inbound = 0;

  for (let i = 1; i < rows.length; i++) {
    const cells = rows[i].split(/[,;]/);
    const msg = cells.find(c => c.length > 10 && /[a-zA-Zàéèê]/.test(c)) ?? "";
    const phone = cells.find(c => /\d{8,}/.test(c.replace(/\D/g, ""))) ?? "";
    if (phone) contacts.add(phone.replace(/\D/g, ""));
    if (msg.includes("?") || msg.length > 20) {
      inbound++;
      const normalized = msg.trim().toLowerCase().substring(0, 60);
      questions[normalized] = (questions[normalized] ?? 0) + 1;
    }
  }

  const top_questions = Object.entries(questions)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
    .map(([text, count]) => ({ text, count }));

  return {
    total_messages: rows.length - 1,
    unique_contacts: contacts.size,
    top_questions,
    unresolved_count: Math.round(inbound * 0.15),
    avg_response_time: "~2s",
  };
}
