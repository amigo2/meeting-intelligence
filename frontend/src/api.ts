// Thin API client for the Meeting Intelligence backend.
const BASE = "http://localhost:8001";

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
export type AskResult = { answer: string; sources: Source[] };

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
