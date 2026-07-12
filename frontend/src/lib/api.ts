// Empty string = same-origin (Railway all-in-one via Next rewrites)
const API_URL =
  process.env.NEXT_PUBLIC_API_URL !== undefined
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000";

export type Plan = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  monthly_quota: number;
  price_yen: number;
  sort_order: number;
  is_active: boolean;
};

export type Subscription = {
  id?: number;
  user_id?: number;
  plan_id?: number | null;
  plan_code?: string | null;
  plan_name: string;
  monthly_quota: number;
  used_count: number;
  remaining: number;
  period_start: string;
  period_end: string;
  status: string;
  auto_renew: boolean;
  is_active: boolean;
  cancelled_at?: string | null;
  price_yen?: number | null;
  user_name?: string | null;
  user_email?: string | null;
};

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  google_calendar_connected: boolean;
  subscription?: Subscription | null;
};

export type Studio = {
  id: number;
  name: string;
  description: string | null;
  capacity: number;
  is_active: boolean;
};

export type TimeSlot = {
  id: number;
  studio_id: number;
  start_at: string;
  end_at: string;
  is_available: boolean;
  studio_name?: string | null;
};

export type Invoice = {
  id: number;
  user_id: number;
  subscription_id?: number | null;
  number: string;
  status: string;
  kind: string;
  description?: string | null;
  currency: string;
  subtotal_yen: number;
  tax_yen: number;
  total_yen: number;
  amount_paid_yen: number;
  proration_yen: number;
  period_start?: string | null;
  period_end?: string | null;
  stripe_invoice_id?: string | null;
  hosted_invoice_url?: string | null;
  invoice_pdf_url?: string | null;
  line_items: { label: string; amount_yen: number }[];
  paid_at?: string | null;
  created_at: string;
  user_name?: string | null;
  user_email?: string | null;
};

export type ProrationPreview = {
  from_plan_code: string;
  from_plan_name: string;
  to_plan_code: string;
  to_plan_name: string;
  old_price_yen: number;
  new_price_yen: number;
  period_start: string;
  period_end: string;
  remaining_days: number;
  total_days: number;
  unused_credit_yen: number;
  new_charge_yen: number;
  proration_yen: number;
  tax_yen: number;
  total_due_yen: number;
  direction: string;
  explanation: string;
};

export type BillingConfig = {
  stripe_enabled: boolean;
  publishable_key?: string | null;
  smtp_enabled: boolean;
  tax_rate: number;
  demo_mode: boolean;
};

export type ChangePlanResult = {
  subscription: Subscription;
  proration: ProrationPreview;
  invoice: Invoice;
};

export type Reservation = {
  id: number;
  user_id: number;
  studio_id: number;
  time_slot_id: number;
  status: string;
  note: string | null;
  google_event_id: string | null;
  created_at: string;
  cancelled_at: string | null;
  studio_name?: string | null;
  user_name?: string | null;
  user_email?: string | null;
  start_at?: string | null;
  end_at?: string | null;
};

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = "リクエストに失敗しました";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "ログインに失敗しました");
  }
  const data = await res.json();
  return data.access_token as string;
}

export async function register(
  email: string,
  password: string,
  full_name: string,
  plan_code?: string,
) {
  return request<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name, plan_code }),
  });
}

export const api = {
  me: () => request<User>("/api/auth/me"),
  studios: () => request<Studio[]>("/api/studios"),
  slots: (params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    return request<TimeSlot[]>(`/api/slots${qs}`);
  },
  reservations: (params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    return request<Reservation[]>(`/api/reservations${qs}`);
  },
  reservation: (id: number) => request<Reservation>(`/api/reservations/${id}`),
  createReservation: (time_slot_id: number, note?: string) =>
    request<Reservation>("/api/reservations", {
      method: "POST",
      body: JSON.stringify({ time_slot_id, note }),
    }),
  cancelReservation: (id: number) =>
    request<Reservation>(`/api/reservations/${id}/cancel`, { method: "POST" }),
  googleAuthUrl: () => request<{ url: string; configured: boolean }>("/api/google/auth-url"),
  googleDisconnect: () => request<{ message: string }>("/api/google/disconnect", { method: "DELETE" }),
  plans: () => request<Plan[]>("/api/plans"),
  mySubscription: () => request<Subscription>("/api/subscriptions/me"),
  changePlan: async (plan_code: string) => {
    const result = await request<ChangePlanResult>("/api/subscriptions/change-plan", {
      method: "POST",
      body: JSON.stringify({ plan_code }),
    });
    return result;
  },
  previewChangePlan: (plan_code: string) =>
    request<ProrationPreview>("/api/subscriptions/change-plan/preview", {
      method: "POST",
      body: JSON.stringify({ plan_code }),
    }),
  cancelSubscription: () =>
    request<Subscription>("/api/subscriptions/cancel", { method: "POST" }),
  reactivateSubscription: (plan_code?: string) =>
    request<Subscription>("/api/subscriptions/reactivate", {
      method: "POST",
      body: JSON.stringify({ plan_code: plan_code || null }),
    }),
  renewSubscription: () =>
    request<Subscription>("/api/subscriptions/renew", { method: "POST" }),
  billingConfig: () => request<BillingConfig>("/api/billing/config"),
  checkout: (plan_code: string) =>
    request<{ id: string; url: string; mode: string; invoice?: Invoice }>("/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_code }),
    }),
  billingPortal: () => request<{ url: string }>("/api/billing/portal", { method: "POST" }),
  invoices: () => request<Invoice[]>("/api/billing/invoices"),
  invoice: (id: number) => request<Invoice>(`/api/billing/invoices/${id}`),
  notifications: () =>
    request<{ id: number; to_email: string; subject: string; template_key: string; status: string; created_at: string }[]>(
      "/api/billing/notifications",
    ),
  adminSubscriptions: () => request<Subscription[]>("/api/admin/subscriptions"),
  adminUpdateSubscription: (
    userId: number,
    payload: {
      plan_code?: string;
      status?: string;
      auto_renew?: boolean;
      used_count?: number;
      monthly_quota?: number;
    },
  ) =>
    request<Subscription>(`/api/admin/subscriptions/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(iso));
}

export function formatYen(value?: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("ja-JP", { style: "currency", currency: "JPY" }).format(value);
}

export function statusLabel(status: string): string {
  if (status === "confirmed") return "確定";
  if (status === "cancelled") return "キャンセル済";
  if (status === "active") return "有効";
  if (status === "expired") return "期限切れ";
  return status;
}

export function subscriptionStatusLabel(status: string): string {
  if (status === "active") return "有効";
  if (status === "cancelled") return "解約予定";
  if (status === "expired") return "期限切れ";
  if (status === "past_due") return "支払遅延";
  return status;
}

export function receiptUrl(invoiceId: number): string {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const base = API_URL || "";
  // HTML receipt needs Authorization; open via dedicated page that fetches with token
  return `/subscription/invoices/${invoiceId}`;
}
