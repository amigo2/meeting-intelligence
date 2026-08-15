// Thin API client for the Meeting Intelligence backend.
// Prod: "" (same-origin — CloudFront proxies /meetings/* to the ALB).
// Dev:  set VITE_API_BASE=http://localhost:8001 (see .env.development).
const BASE = import.meta.env.VITE_API_BASE ?? "";

export type ActionItem = { owner: string; task: string; due: string | null };
export type Intelligence = {
  summary: string;
  decisions: string[];
  action_items: ActionItem[];
};
export type Source = {
  text: string;
  speakers: string[];
  start: string;
  end: string;
  similarity: number;
};
// The runtime faithfulness gate's verdict (absent on refusals / un-verified answers).
export type Verification = {
  grounded: boolean;
  unsupported: string[];
  fabricated_citations: string[];
};
export type AskResult = { answer: string; sources: Source[]; verification?: Verification };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function loadSample(meetingId: string, sample: string) {
  return post<{ meeting_id: string; title: string; intelligence: Intelligence }>(
    `/meetings/${meetingId}/load-sample`,
    { sample }
  );
}

export function ask(meetingId: string, question: string) {
  return post<AskResult>(`/meetings/${meetingId}/ask`, { question });
}
