/**
 * OpenAI Chat Completions — used for FEED_MODE=gpt and /api/analyze.
 * Env: OPENAI_API_KEY (required), OPENAI_MODEL (default gpt-4o-mini)
 */

const OPENAI_CHAT = "https://api.openai.com/v1/chat/completions";

export async function openaiChatJson<T>(params: {
  system: string;
  user: string;
}): Promise<T> {
  const key = process.env.OPENAI_API_KEY?.trim();
  if (!key) {
    throw new Error("OPENAI_API_KEY is not set");
  }
  const model = process.env.OPENAI_MODEL?.trim() || "gpt-4o-mini";

  const res = await fetch(OPENAI_CHAT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: params.system },
        { role: "user", content: params.user },
      ],
      temperature: 0.55,
    }),
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`OpenAI HTTP ${res.status}: ${text.slice(0, 600)}`);
  }

  let data: { choices?: { message?: { content?: string } }[] };
  try {
    data = JSON.parse(text) as typeof data;
  } catch {
    throw new Error(`OpenAI returned non-JSON: ${text.slice(0, 200)}`);
  }

  const raw = data.choices?.[0]?.message?.content?.trim() ?? "";
  if (!raw) throw new Error("OpenAI returned empty content");

  let stripped = raw;
  if (stripped.startsWith("```")) {
    stripped = stripped.replace(/^```(?:json)?\s*/i, "").replace(/\s*```\s*$/i, "");
  }

  try {
    return JSON.parse(stripped) as T;
  } catch {
    throw new Error(`OpenAI content was not valid JSON: ${stripped.slice(0, 300)}`);
  }
}

export async function openaiChatText(params: {
  system: string;
  user: string;
}): Promise<string> {
  const key = process.env.OPENAI_API_KEY?.trim();
  if (!key) throw new Error("OPENAI_API_KEY is not set");
  const model = process.env.OPENAI_MODEL?.trim() || "gpt-4o-mini";

  const res = await fetch(OPENAI_CHAT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: params.system },
        { role: "user", content: params.user },
      ],
      temperature: 0.4,
    }),
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`OpenAI HTTP ${res.status}: ${text.slice(0, 600)}`);
  }
  const data = JSON.parse(text) as { choices?: { message?: { content?: string } }[] };
  return data.choices?.[0]?.message?.content?.trim() ?? "";
}
