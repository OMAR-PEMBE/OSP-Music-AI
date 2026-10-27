export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, unknown>;

  constructor(
    message: string,
    status: number,
    code = "request_error",
    fields: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

function cookieValue(name: string): string | null {
  if (typeof document === "undefined") return null;
  const pair = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));
  return pair ? decodeURIComponent(pair.slice(name.length + 1)) : null;
}

async function csrfToken(): Promise<string> {
  const existing = cookieValue("csrftoken");
  if (existing) return existing;
  const response = await fetch("/api/csrf", { credentials: "same-origin" });
  const data = (await response.json()) as { csrfToken?: string };
  if (!response.ok || !data.csrfToken) {
    throw new ApiError("Could not start a secure session.", response.status);
  }
  return data.csrfToken;
}

type ApiOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export async function api<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  let body: BodyInit | undefined;

  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
    headers.set("X-CSRFToken", await csrfToken());
  }

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    body,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (response.status === 204) return undefined as T;

  const data = (await response.json().catch(() => ({}))) as {
    error?: {
      code?: string;
      message?: string;
      fields?: Record<string, unknown>;
    };
    detail?: string;
  };
  if (!response.ok) {
    throw new ApiError(
      data.error?.message ??
        data.detail ??
        "The request could not be completed.",
      response.status,
      data.error?.code,
      data.error?.fields,
    );
  }
  return data as T;
}

export type ApiConfig = {
  song_price_tzs: number;
  min_topup_tzs: number;
  max_topup_tzs: number;
  topup_presets_tzs: number[];
  generation_enabled: boolean;
  payment_demo: boolean;
  lyrics_daily_limit: number;
  support_whatsapp: string;
  genres: string[];
};

export type Me = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  avatar_url: string | null;
  language: "en";
  theme: "system" | "light" | "dark";
  email_verified: boolean;
  balance_tzs: number;
  unseen_songs: number;
};

export type SongVersion = {
  index: number;
  status: "pending" | "streaming" | "ready" | "failed";
  stream_url: string | null;
  duration_ms: number | null;
};

export type SongJob = {
  id: string;
  title: string;
  genre: string;
  language: string;
  status:
    | "queued"
    | "submitting"
    | "running"
    | "streaming"
    | "ready"
    | "partial"
    | "failed";
  price_tzs: number;
  refund_tzs: number;
  created_at: string;
  finished_at: string | null;
  lyrics: string;
  versions: SongVersion[];
};

export type Transaction = {
  id: string;
  type: "topup" | "song_charge" | "song_refund" | "adjustment";
  amount_tzs: number;
  balance_after_tzs: number;
  created_at: string;
  song_title: string | null;
  payment_status: string | null;
};

export type PageResult<T> = {
  results: T[];
  next: number | null;
  count: number;
};

export function formatTzs(amount: number): string {
  return new Intl.NumberFormat("en-TZ", {
    style: "currency",
    currency: "TZS",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-TZ", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Africa/Dar_es_Salaam",
  }).format(new Date(value));
}
