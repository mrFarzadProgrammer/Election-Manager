import {
    User,
    CandidateData as Candidate,
    Plan,
    Ticket,
    Announcement,
    FeedbackSubmission,
    FeedbackStatsResponse,
    QuestionSubmission,
    BotRequestSubmission,
    AdminDashboardStats,
    MvpOverviewResponse,
    BehaviorStatsResponse,
    FlowPathsResponse,
    QuestionLearningItem,
    CommitmentLearningItem,
    Commitment,
    CommitmentTermsAcceptance,
    LeadItem,
    UxLogItem,
    GlobalBotUserItem,
    TechnicalErrorItem,
    MonitoringUxLogItem,
    HealthCheckItem,
    FlowDropItem,
} from "../types";

const VITE_API_BASE =
    (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_URL) ||
    undefined;

export const API_BASE =
    VITE_API_BASE ||
    (typeof process !== "undefined" && (process as any).env?.REACT_APP_API_BASE_URL) ||
    (() => {
        // In Vite dev, prefer same-origin requests and rely on Vite proxy (/api, /uploads).
        try {
            if (typeof import.meta !== "undefined" && (import.meta as any).env?.DEV) {
                return "";
            }
        } catch {
            // ignore
        }

        // Safe default for local dev. If the UI is opened via a LAN hostname/IP,
        // point API calls to the same host on port 8000.
        try {
            if (typeof window !== "undefined" && window.location?.hostname) {
                const host = String(window.location.hostname || "").trim();
                if (host && host !== "localhost" && host !== "127.0.0.1") {
                    return `http://${host}:8000`;
                }
            }
        } catch {
            // ignore
        }
        return "http://127.0.0.1:8000";
    })();

const normalizeAbsoluteUrl = (url: any): any => {
    if (typeof url !== "string") return url;
    const trimmed = url.trim();
    if (!trimmed) return url;

    const knownBases = ["http://localhost:8000", "http://127.0.0.1:8000"];
    for (const base of knownBases) {
        if (trimmed.startsWith(base + "/")) {
            return API_BASE.replace(/\/$/, "") + trimmed.slice(base.length);
        }
    }
    return url;
};

type ApiErrorPayload =
    | { detail?: any; message?: string }
    | any;

const extractApiMessage = (payload: ApiErrorPayload, fallback: string) => {
    const d = payload?.detail;

    if (typeof d === "string" && d.trim()) return d;
    if (d && typeof d === "object") {
        if (typeof d.message === "string" && d.message.trim()) return d.message;
        if (Array.isArray(d) && d.length) {
            const first = d[0];
            const msg = first?.msg || first?.message;
            if (typeof msg === "string" && msg.trim()) return msg;
        }
    }
    if (typeof payload?.message === "string" && payload.message.trim()) return payload.message;

    return fallback;
};

const readBodySafely = async (res: Response) => {
    const text = await res.text();
    if (!text) return null;
    try {
        return JSON.parse(text);
    } catch {
        return { detail: text };
    }
};

type RefreshResponse = {
    access_token: string;
    refresh_token: string;
    token_type: string;
};

const hasAuthorizationHeader = (headers?: RequestInit["headers"]) => {
    if (!headers) return false;
    if (headers instanceof Headers) return headers.has("Authorization");
    if (Array.isArray(headers)) return headers.some(([k]) => String(k).toLowerCase() === "authorization");
    return Object.keys(headers as any).some((k) => k.toLowerCase() === "authorization");
};

const setAuthorizationHeader = (headers: RequestInit["headers"], value: string) => {
    const h = new Headers(headers as any);
    h.set("Authorization", value);
    return h;
};

const normalizeAuthorizationValue = (value: any): string => {
    const raw = String(value ?? "").trim();
    if (!raw) return "";

    // Remove control characters that can make fetch() throw (e.g., CR/LF).
    const cleaned = raw.replace(/[\u0000-\u001F\u007F]/g, "").trim();
    if (!cleaned) return "";

    const m = /^Bearer\s+(.*)$/i.exec(cleaned);
    const candidate = (m ? m[1] : cleaned).trim();
    if (!candidate) return "";

    // Prefer extracting a real JWT if the stored value got polluted.
    const jwtMatch = candidate.match(/[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/);
    const token = (jwtMatch?.[0] || candidate)
        // Strip everything not expected in JWT/base64url and separators.
        .replace(/[^A-Za-z0-9_.-]/g, "")
        .trim();

    return token ? `Bearer ${token}` : "";
};

const normalizeRequestHeaders = (headers?: RequestInit["headers"]) => {
    if (!headers) return headers;
    const h = new Headers(headers as any);

    if (h.has("Authorization")) {
        const next = normalizeAuthorizationValue(h.get("Authorization"));
        if (next) h.set("Authorization", next);
        else h.delete("Authorization");
    }
    return h;
};

const getCookie = (name: string): string | null => {
    try {
        if (typeof document === "undefined") return null;
        const encoded = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${encoded}=([^;]*)`));
        return match ? decodeURIComponent(match[1]) : null;
    } catch {
        return null;
    }
};

const maybeAttachCsrfHeader = (headers: Headers, method: string) => {
    const m = String(method || "GET").toUpperCase();
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(m)) return;
    if (headers.has("X-CSRF-Token")) return;
    const csrf = getCookie("csrf_token");
    if (csrf) headers.set("X-CSRF-Token", csrf);
};

const refreshAccessToken = async (): Promise<RefreshResponse | null> => {
    try {
        // Prefer cookie-based refresh (HttpOnly refresh_token cookie).
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
        });

        if (res.ok) {
            const data = (await res.json()) as RefreshResponse;
            if (data?.access_token) {
                // Legacy compatibility: if the app is still using localStorage tokens, keep them updated.
                if (localStorage.getItem("refresh_token")) {
                    localStorage.setItem("access_token", data.access_token);
                    if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
                }
                return data;
            }
        }
    } catch {
        // ignore
    }

    // Fallback: legacy refresh_token in localStorage.
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return null;
    try {
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) return null;
        const data = (await res.json()) as RefreshResponse;
        if (!data?.access_token) return null;

        localStorage.setItem("access_token", data.access_token);
        if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
        return data;
    } catch {
        return null;
    }
};

async function request<T>(path: string, options: RequestInit = {}, _retried: boolean = false): Promise<T> {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

    const normalizedHeaders = normalizeRequestHeaders(options.headers);
    const headers = new Headers(normalizedHeaders as any);
    maybeAttachCsrfHeader(headers, options.method || "GET");

    const normalizedOptions: RequestInit = {
        ...options,
        credentials: options.credentials ?? "include",
        headers,
    };

    let res: Response;
    try {
        res = await fetch(url, normalizedOptions);
    } catch (e: any) {
        // In browsers, CORS failures or invalid header values often surface as a generic fetch() error.
        // Keep the user-friendly message, but also log the underlying error for debugging.
        try {
            console.error("API fetch failed:", { url, options: normalizedOptions, error: e });
        } catch {
            // ignore
        }
        const origin = (() => {
            try {
                return typeof window !== "undefined" ? window.location?.origin : "";
            } catch {
                return "";
            }
        })();
        const reason = (() => {
            try {
                const msg = String(e?.message ?? e ?? "").trim();
                return msg ? ` | Reason: ${msg}` : "";
            } catch {
                return "";
            }
        })();
        throw new Error(
            `ارتباط با سرور برقرار نشد. لطفاً اتصال یا اجرای سرور را بررسی کنید. (API: ${API_BASE}${origin ? ` | Origin: ${origin}` : ""}${reason})`
        );
    }

    if (!res.ok) {
        // If session expired, try refreshing once and retry the original request.
        const isAuthPath = /^\/api\/auth\//.test(path);
        if (res.status === 401 && !_retried && !isAuthPath) {
            const hadAuthHeader = hasAuthorizationHeader(normalizedOptions.headers);
            const refreshed = await refreshAccessToken();

            if (refreshed?.access_token) {
                if (hadAuthHeader) {
                    const nextHeaders = setAuthorizationHeader(normalizedOptions.headers, `Bearer ${refreshed.access_token}`);
                    return request<T>(path, { ...normalizedOptions, headers: nextHeaders }, true);
                }
                // Cookie-based: refresh updates cookies; retry the same request.
                return request<T>(path, normalizedOptions, true);
            }

            if (hadAuthHeader) {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
            }
            throw new Error("نشست شما منقضی شده است. لطفاً دوباره وارد شوید.");
        }

        const payload = await readBodySafely(res);
        const fallback = `خطا در درخواست (${res.status})`;
        const message = extractApiMessage(payload, fallback);

        throw new Error(message);
    }

    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return (await res.json()) as T;
    }
    return (await res.text()) as unknown as T;
}

async function requestBlob(path: string, options: RequestInit = {}, _retried: boolean = false): Promise<Blob> {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

    const normalizedHeaders = normalizeRequestHeaders(options.headers);
    const headers = new Headers(normalizedHeaders as any);
    maybeAttachCsrfHeader(headers, options.method || "GET");

    const normalizedOptions: RequestInit = {
        ...options,
        credentials: options.credentials ?? "include",
        headers,
    };

    let res: Response;
    try {
        res = await fetch(url, normalizedOptions);
    } catch {
        throw new Error("ارتباط با سرور برقرار نشد. لطفاً اتصال یا اجرای سرور را بررسی کنید.");
    }

    if (!res.ok) {
        const isAuthPath = /^\/api\/auth\//.test(path);
        if (res.status === 401 && !_retried && !isAuthPath) {
            const hadAuthHeader = hasAuthorizationHeader(normalizedOptions.headers);
            const refreshed = await refreshAccessToken();
            if (refreshed?.access_token) {
                if (hadAuthHeader) {
                    const nextHeaders = setAuthorizationHeader(normalizedOptions.headers, `Bearer ${refreshed.access_token}`);
                    return requestBlob(path, { ...normalizedOptions, headers: nextHeaders }, true);
                }
                return requestBlob(path, normalizedOptions, true);
            }
            if (hadAuthHeader) {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
            }
            throw new Error("نشست شما منقضی شده است. لطفاً دوباره وارد شوید.");
        }

        const payload = await readBodySafely(res);
        const fallback = `خطا در درخواست (${res.status})`;
        const message = extractApiMessage(payload, fallback);
        throw new Error(message);
    }

    return await res.blob();
}

const mapCandidate = (c: any): Candidate => ({
    ...c,
    id: String(c.id),
    name: c.name || c.full_name || c.username,
    full_name: c.full_name || c.name,
    botName: c.bot_name || c.botName,
    botToken: c.bot_token || c.botToken,
    isActive: c.is_active ?? c.isActive,
    userCount: c.vote_count ?? c.userCount ?? 0,
    created_at_jalali: c.created_at_jalali || c.createdAtJalali,
    active_plan_id: c.active_plan_id ? String(c.active_plan_id) : undefined,
    plan_start_date: c.plan_start_date,
    plan_expires_at: c.plan_expires_at,
    image_url: normalizeAbsoluteUrl(c.image_url),
    voice_url: normalizeAbsoluteUrl(c.voice_url),
});

const mapPlan = (p: any): Plan => ({
    ...p,
    id: String(p.id),
    price: String(p.price),
    features: p.features || [],
    is_visible: p.is_visible ?? false,
    created_at_jalali: p.created_at_jalali
});

const ensureUtc = (dateStr: string) => {
    if (!dateStr) return Date.now();
    // If it doesn't end in Z and looks like ISO, append Z to treat as UTC
    if (dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
        return new Date(dateStr + 'Z').getTime();
    }
    return new Date(dateStr).getTime();
};

const normalizeIsoUtcString = (value: any): string => {
    if (typeof value !== 'string') return String(value ?? '');
    const s = value.trim();
    if (!s) return '';
    // If it's an ISO-like timestamp without timezone, treat it as UTC.
    // Example from FastAPI (naive UTC): 2026-02-07T17:14:37.123456
    if (s.includes('T') && !/(Z|[+-]\d{2}:\d{2})$/.test(s)) {
        return s + 'Z';
    }
    return s;
};

const mapTicket = (t: any): Ticket => ({
    ...t,
    id: String(t.id),
    user_id: String(t.user_id),
    userName: t.userName || t.user_name || t.username,
    lastUpdate: t.updated_at ? ensureUtc(t.updated_at) : Date.now(),
    messages: (t.messages || []).map((m: any) => ({
        ...m,
        id: String(m.id),
        senderId: String(m.senderId || m.sender_id || 'unknown'),
        senderRole: m.senderRole || m.sender_role,
        timestamp: m.created_at ? ensureUtc(m.created_at) : Date.now(),
        attachmentUrl: m.attachmentUrl || m.attachment_url,
        attachmentType: m.attachmentType || m.attachment_type,
    }))
});

const mapFeedbackSubmission = (s: any): FeedbackSubmission => ({
    ...s,
    id: String(s.id),
    candidate_id: String(s.candidate_id),
    text: String(s.text ?? ''),
    created_at: normalizeIsoUtcString(s.created_at),
    constituency: typeof s.constituency === 'string' ? s.constituency : undefined,
    status: (s.status || 'NEW'),
    tag: s.tag ?? null,
});

const mapQuestionSubmission = (s: any): QuestionSubmission => ({
    ...s,
    id: String(s.id),
    candidate_id: String(s.candidate_id),
    text: String(s.text ?? ''),
    created_at: normalizeIsoUtcString(s.created_at),
    topic: typeof s.topic === 'string' ? s.topic : (s.topic ?? null),
    constituency: typeof s.constituency === 'string' ? s.constituency : undefined,
    status: (String(s.status || 'PENDING').toUpperCase() as any),
    answer_text: s.answer_text ?? s.answer ?? null,
    answered_at: s.answered_at ? normalizeIsoUtcString(s.answered_at) : null,
    is_public: Boolean(s.is_public ?? false),
    is_featured: Boolean(s.is_featured ?? false),
});

const mapBotRequestSubmission = (s: any): BotRequestSubmission => ({
    ...s,
    id: String(s.id),
    candidate_id: String(s.candidate_id),
    telegram_user_id: String(s.telegram_user_id ?? ''),
    telegram_username: s.telegram_username ?? null,
    requester_full_name: s.requester_full_name ?? null,
    requester_contact: s.requester_contact ?? null,
    role: s.role ?? s.topic ?? null,
    constituency: s.constituency ?? null,
    status: String(s.status ?? 'new_request'),
    text: String(s.text ?? ''),
    created_at: normalizeIsoUtcString(s.created_at),
});

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export const api = {
    // ========== Auth ==========
    login: async (username: string, password: string): Promise<AuthResponse> => {
        return request<AuthResponse>("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
    },

    register: async (
        username: string,
        email: string,
        full_name: string,
        password: string
    ): Promise<AuthResponse> => {
        return request<AuthResponse>("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, full_name, password }),
        });
    },

    logout: async (): Promise<void> => {
        await request<void>("/api/auth/logout", {
            method: "POST",
        });
    },

    getMe: async (token: string = ""): Promise<User> => {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const user = await request<any>("/api/auth/me", {
            method: "GET",
            headers,
        });
        return { ...user, id: String(user.id) };
    },

    uploadFile: async (
        file: File,
        token: string = "",
        opts: { visibility?: "public" | "private" } = {}
    ): Promise<{ url: string }> => {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const form = new FormData();
        form.append("file", file);
        if (opts.visibility) form.append("visibility", opts.visibility);

        return request<{ url: string }>("/api/upload", {
            method: "POST",
            headers,
            body: form,
        });
    },

    uploadVoiceIntro: async (
        file: File,
        token: string = "",
        opts: { candidate_name?: string } = {}
    ): Promise<{ url: string }> => {
        const headers: Record<string, string> = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const form = new FormData();
        form.append("file", file);
        if (opts.candidate_name) form.append("candidate_name", opts.candidate_name);
        return request<{ url: string }>("/api/upload/voice-intro", {
            method: "POST",
            headers,
            body: form,
        });
    },

    // ========== Admin Dashboard (MVP) ==========
    getAdminDashboardStats: async (token: string): Promise<AdminDashboardStats> => {
        return request<AdminDashboardStats>("/api/admin/dashboard-stats", {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    // ========== Admin Learning (MVP) ==========
    getAdminMvpOverview: async (token: string): Promise<MvpOverviewResponse> => {
        return request<MvpOverviewResponse>("/api/admin/mvp/overview", {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpBehavior: async (token: string, candidateId?: number | null): Promise<BehaviorStatsResponse> => {
        const qs = candidateId == null ? "" : `?candidate_id=${encodeURIComponent(String(candidateId))}`;
        return request<BehaviorStatsResponse>(`/api/admin/mvp/behavior${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpPaths: async (
        token: string,
        opts: { candidateId?: number | null; limit?: number } = {}
    ): Promise<FlowPathsResponse> => {
        const params = new URLSearchParams();
        if (opts.candidateId != null) params.set("candidate_id", String(opts.candidateId));
        if (opts.limit != null) params.set("limit", String(opts.limit));
        const qs = params.toString() ? `?${params.toString()}` : "";
        return request<FlowPathsResponse>(`/api/admin/mvp/paths${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpQuestions: async (
        token: string,
        opts: { candidateId?: number | null; status?: string | null } = {}
    ): Promise<QuestionLearningItem[]> => {
        const params = new URLSearchParams();
        if (opts.candidateId != null) params.set("candidate_id", String(opts.candidateId));
        if (opts.status) params.set("status", opts.status);
        const qs = params.toString() ? `?${params.toString()}` : "";
        return request<QuestionLearningItem[]>(`/api/admin/mvp/questions${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpCommitments: async (
        token: string,
        candidateId?: number | null
    ): Promise<CommitmentLearningItem[]> => {
        const qs = candidateId == null ? "" : `?candidate_id=${encodeURIComponent(String(candidateId))}`;
        return request<CommitmentLearningItem[]>(`/api/admin/mvp/commitments${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpLeads: async (token: string, candidateId?: number | null): Promise<LeadItem[]> => {
        const qs = candidateId == null ? "" : `?candidate_id=${encodeURIComponent(String(candidateId))}`;
        return request<LeadItem[]>(`/api/admin/mvp/leads${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpUxLogs: async (
        token: string,
        opts: { candidateId?: number | null; action?: string | null; limit?: number } = {}
    ): Promise<UxLogItem[]> => {
        const params = new URLSearchParams();
        if (opts.candidateId != null) params.set("candidate_id", String(opts.candidateId));
        if (opts.action) params.set("action", opts.action);
        if (opts.limit != null) params.set("limit", String(opts.limit));
        const qs = params.toString() ? `?${params.toString()}` : "";
        return request<UxLogItem[]>(`/api/admin/mvp/ux-logs${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getAdminMvpGlobalUsers: async (
        token: string,
        opts: {
            representativeId?: number | null;
            startDate?: string | null;
            endDate?: string | null;
            interactionType?: "question" | "comment" | "lead" | null;
            limit?: number | null;
        } = {}
    ): Promise<GlobalBotUserItem[]> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set("representative_id", String(opts.representativeId));
        if (opts.startDate) params.set("start_date", opts.startDate);
        if (opts.endDate) params.set("end_date", opts.endDate);
        if (opts.interactionType) params.set("interaction_type", opts.interactionType);
        if (opts.limit != null) params.set("limit", String(opts.limit));
        const qs = params.toString() ? `?${params.toString()}` : "";
        return request<GlobalBotUserItem[]>(`/api/admin/mvp/global-users${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    exportAdminMvpGlobalUsersXlsx: async (
        token: string,
        opts: {
            representativeId?: number | null;
            startDate?: string | null;
            endDate?: string | null;
            interactionType?: "question" | "comment" | "lead" | null;
        } = {}
    ): Promise<Blob> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set("representative_id", String(opts.representativeId));
        if (opts.startDate) params.set("start_date", opts.startDate);
        if (opts.endDate) params.set("end_date", opts.endDate);
        if (opts.interactionType) params.set("interaction_type", opts.interactionType);
        const qs = params.toString() ? `?${params.toString()}` : "";
        return requestBlob(`/api/admin/mvp/global-users/export.xlsx${qs}`, {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    // ========== Admin Monitoring (Super Admin) ==========
    getMonitoringErrors: async (
        token: string,
        opts: { representativeId?: number | null; startDate?: string | null; endDate?: string | null; limit?: number | null } = {}
    ): Promise<TechnicalErrorItem[]> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set('representative_id', String(opts.representativeId));
        if (opts.startDate) params.set('start_date', opts.startDate);
        if (opts.endDate) params.set('end_date', opts.endDate);
        if (opts.limit != null) params.set('limit', String(opts.limit));
        const qs = params.toString() ? `?${params.toString()}` : '';
        return request<TechnicalErrorItem[]>(`/api/admin/monitoring/errors${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    exportMonitoringErrorsXlsx: async (
        token: string,
        opts: { representativeId?: number | null; startDate?: string | null; endDate?: string | null } = {}
    ): Promise<Blob> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set('representative_id', String(opts.representativeId));
        if (opts.startDate) params.set('start_date', opts.startDate);
        if (opts.endDate) params.set('end_date', opts.endDate);
        const qs = params.toString() ? `?${params.toString()}` : '';
        return requestBlob(`/api/admin/monitoring/errors/export.xlsx${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    getMonitoringUxLogs: async (
        token: string,
        opts: {
            representativeId?: number | null;
            startDate?: string | null;
            endDate?: string | null;
            action?: string | null;
            limit?: number | null;
        } = {}
    ): Promise<MonitoringUxLogItem[]> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set('representative_id', String(opts.representativeId));
        if (opts.startDate) params.set('start_date', opts.startDate);
        if (opts.endDate) params.set('end_date', opts.endDate);
        if (opts.action) params.set('action', opts.action);
        if (opts.limit != null) params.set('limit', String(opts.limit));
        const qs = params.toString() ? `?${params.toString()}` : '';
        return request<MonitoringUxLogItem[]>(`/api/admin/monitoring/ux-logs${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    exportMonitoringUxLogsXlsx: async (
        token: string,
        opts: { representativeId?: number | null; startDate?: string | null; endDate?: string | null; action?: string | null } = {}
    ): Promise<Blob> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set('representative_id', String(opts.representativeId));
        if (opts.startDate) params.set('start_date', opts.startDate);
        if (opts.endDate) params.set('end_date', opts.endDate);
        if (opts.action) params.set('action', opts.action);
        const qs = params.toString() ? `?${params.toString()}` : '';
        return requestBlob(`/api/admin/monitoring/ux-logs/export.xlsx${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    getMonitoringHealthChecks: async (
        token: string,
        opts: { representativeId?: number | null; checkType?: string | null; limit?: number | null } = {}
    ): Promise<HealthCheckItem[]> => {
        const params = new URLSearchParams();
        if (opts.representativeId != null) params.set('representative_id', String(opts.representativeId));
        if (opts.checkType) params.set('check_type', opts.checkType);
        if (opts.limit != null) params.set('limit', String(opts.limit));
        const qs = params.toString() ? `?${params.toString()}` : '';
        return request<HealthCheckItem[]>(`/api/admin/monitoring/health-checks${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    getMonitoringFlowDrops: async (
        token: string,
        representativeId?: number | null
    ): Promise<FlowDropItem[]> => {
        const qs = representativeId == null ? '' : `?representative_id=${encodeURIComponent(String(representativeId))}`;
        return request<FlowDropItem[]>(`/api/admin/monitoring/flow-drops${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    exportMonitoringFlowDropsXlsx: async (
        token: string,
        representativeId?: number | null
    ): Promise<Blob> => {
        const qs = representativeId == null ? '' : `?representative_id=${encodeURIComponent(String(representativeId))}`;
        return requestBlob(`/api/admin/monitoring/flow-drops/export.xlsx${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
    },

    // ========== Admin: Bot Requests (Build bot) ==========
    getBotRequests: async (token: string, status?: string): Promise<BotRequestSubmission[]> => {
        const qs = status ? `?status=${encodeURIComponent(status)}` : '';
        const data = await request<any[]>(`/api/admin/bot-requests${qs}`, {
            method: 'GET',
            headers: { Authorization: `Bearer ${token}` },
        });
        return (data || []).map(mapBotRequestSubmission);
    },

    updateBotRequestStatus: async (id: string, status: string, token: string): Promise<BotRequestSubmission> => {
        const data = await request<any>(`/api/admin/bot-requests/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ status }),
        });
        return mapBotRequestSubmission(data);
    },

    // ========== Candidates ==========
    getCandidate: async (id: number, token?: string): Promise<Candidate> => {
        const headers: any = { "Content-Type": "application/json" };
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const data = await request<any>(`/api/candidates/${id}`, {
            method: "GET",
            headers,
        });
        return mapCandidate(data);
    },

    // ========== Feedback Submissions (Candidate MVP) ==========
    getMyFeedbackSubmissions: async (token: string): Promise<FeedbackSubmission[]> => {
        const data = await request<any[]>(`/api/candidates/me/feedback`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        });
        return (data || []).map(mapFeedbackSubmission);
    },

    updateMyFeedbackSubmission: async (
        token: string,
        submissionId: string,
        patch: { tag?: string | null; status?: 'NEW' | 'REVIEWED' }
    ): Promise<FeedbackSubmission> => {
        const data = await request<any>(`/api/candidates/me/feedback/${encodeURIComponent(String(submissionId))}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(patch),
        });
        return mapFeedbackSubmission(data);
    },

    getMyFeedbackStats: async (token: string, days: 7 | 30): Promise<FeedbackStatsResponse> => {
        return request<FeedbackStatsResponse>(`/api/candidates/me/feedback/stats?days=${days}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        });
    },

    // ========== Public Questions (Candidate MVP) ==========
    getMyQuestionSubmissions: async (token: string): Promise<QuestionSubmission[]> => {
        const data = await request<any[]>(`/api/candidates/me/questions`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        });
        return (data || []).map(mapQuestionSubmission);
    },

    answerMyQuestionSubmission: async (
        token: string,
        submissionId: string,
        answer_text: string,
        options?: { topic?: string | null; is_featured?: boolean }
    ): Promise<QuestionSubmission> => {
        const data = await request<any>(`/api/candidates/me/questions/${encodeURIComponent(String(submissionId))}/answer`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
                answer_text,
                topic: options?.topic ?? undefined,
                is_featured: options?.is_featured ?? undefined,
            }),
        });
        return mapQuestionSubmission(data);
    },

    rejectMyQuestionSubmission: async (token: string, submissionId: string): Promise<QuestionSubmission> => {
        const data = await request<any>(`/api/candidates/me/questions/${encodeURIComponent(String(submissionId))}/reject`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({}),
        });
        return mapQuestionSubmission(data);
    },

    updateMyQuestionSubmissionMeta: async (
        token: string,
        submissionId: string,
        payload: { topic?: string | null; is_featured?: boolean }
    ): Promise<QuestionSubmission> => {
        const data = await request<any>(`/api/candidates/me/questions/${encodeURIComponent(String(submissionId))}/meta`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        return mapQuestionSubmission(data);
    },

    // ========== Commitments (Candidate Strict) ==========
    getMyCommitmentTermsAcceptance: async (token: string): Promise<CommitmentTermsAcceptance | null> => {
        return request<CommitmentTermsAcceptance | null>(`/api/candidates/me/commitments/terms/acceptance`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        });
    },

    acceptMyCommitmentTerms: async (token: string): Promise<CommitmentTermsAcceptance> => {
        return request<CommitmentTermsAcceptance>(`/api/candidates/me/commitments/terms/accept`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    getMyCommitments: async (token: string): Promise<Commitment[]> => {
        return request<Commitment[]>(`/api/candidates/me/commitments`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        });
    },

    createMyCommitmentDraft: async (
        token: string,
        payload: { title: string; description: string; category: string }
    ): Promise<Commitment> => {
        return request<Commitment>(`/api/candidates/me/commitments`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
    },

    updateMyCommitmentDraft: async (
        token: string,
        commitmentId: number,
        patch: { title?: string; description?: string; category?: string }
    ): Promise<Commitment> => {
        return request<Commitment>(
            `/api/candidates/me/commitments/${encodeURIComponent(String(commitmentId))}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(patch),
            }
        );
    },

    publishMyCommitment: async (token: string, commitmentId: number): Promise<Commitment> => {
        return request<Commitment>(
            `/api/candidates/me/commitments/${encodeURIComponent(String(commitmentId))}/publish`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            }
        );
    },

    updateMyCommitmentStatus: async (
        token: string,
        commitmentId: number,
        status: string
    ): Promise<Commitment> => {
        return request<Commitment>(
            `/api/candidates/me/commitments/${encodeURIComponent(String(commitmentId))}/status`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ status }),
            }
        );
    },

    addMyCommitmentProgressLog: async (
        token: string,
        commitmentId: number,
        note: string
    ): Promise<Commitment> => {
        return request<Commitment>(
            `/api/candidates/me/commitments/${encodeURIComponent(String(commitmentId))}/progress`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ note }),
            }
        );
    },

    deleteMyCommitmentDraft: async (token: string, commitmentId: number): Promise<{ message: string }> => {
        return request<{ message: string }>(
            `/api/candidates/me/commitments/${encodeURIComponent(String(commitmentId))}`,
            {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            }
        );
    },

    getCandidates: async (token?: string | null): Promise<Candidate[]> => {
        try {
            const headers: Record<string, string> = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            const data = await request<any[]>("/api/candidates", {
                method: "GET",
                headers,
            });
            if (!Array.isArray(data)) return [];
            return data.map(mapCandidate);
        } catch (error) {
            console.error("Error fetching candidates:", error);
            return [];
        }
    },

    createCandidate: async (payload: any, token: string): Promise<Candidate> => {
        const data = await request<any>("/api/candidates", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        return mapCandidate(data);
    },

    updateCandidate: async (id: number, payload: any, token: string): Promise<Candidate> => {
        const data = await request<any>(`/api/candidates/${id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        return mapCandidate(data);
    },

    applyTelegramProfile: async (candidateId: string | number, token: string): Promise<any> => {
        return request<any>(`/api/candidates/${candidateId}/apply-telegram-profile`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    updateCandidateStatus: async (id: string, isActive: boolean, token: string): Promise<Candidate> => {
        const data = await request<any>(`/api/candidates/${id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ is_active: isActive }),
        });
        return mapCandidate(data);
    },

    deleteCandidate: async (id: string, token: string): Promise<void> => {
        return request<void>(`/api/candidates/${id}`, {
            method: "DELETE",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    resetCandidatePassword: async (candidateId: number, password: string, token: string): Promise<{ detail: string }> => {
        return request<{ detail: string }>(`/api/candidates/${candidateId}/reset-password`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ password }),
        });
    },

    assignPlan: async (candidateId: string, planId: string, durationDays: number = 30, token: string): Promise<any> => {
        return request<any>(`/api/candidates/${candidateId}/assign-plan`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ plan_id: parseInt(planId), duration_days: durationDays }),
        });
    },

    // ========== Plans ==========
    getPlans: async (): Promise<Plan[]> => {
        try {
            const data = await request<any[]>("/api/plans");
            if (!Array.isArray(data)) return [];
            return data.map(mapPlan);
        } catch (error) {
            console.error("Error fetching plans:", error);
            return [];
        }
    },

    createPlan: async (plan: Partial<Plan>, token: string): Promise<Plan> => {
        const data = await request<any>("/api/plans", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(plan),
        });
        return mapPlan(data);
    },

    updatePlan: async (id: string, plan: Partial<Plan>, token: string): Promise<Plan> => {
        const data = await request<any>(`/api/plans/${id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(plan),
        });
        return mapPlan(data);
    },

    deletePlan: async (id: string, token: string): Promise<void> => {
        return request<void>(`/api/plans/${id}`, {
            method: "DELETE",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
    },

    // ========== Tickets ==========
    getTickets: async (): Promise<Ticket[]> => {
        try {
            const data = await request<any[]>("/api/tickets");
            if (!Array.isArray(data)) return [];
            return data.map(mapTicket);
        } catch (error) {
            console.error("Error fetching tickets:", error);
            return [];
        }
    },

    createTicket: async (subject: string, message: string, token: string): Promise<Ticket> => {
        const data = await request<any>("/api/tickets", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ subject, message }),
        });
        return mapTicket(data);
    },

    addTicketMessage: async (
        ticketId: string,
        text: string,
        senderRole: string,
        token: string,
        attachmentUrl?: string,
        attachmentType?: 'IMAGE' | 'FILE'
    ): Promise<any> => {
        return request<any>(`/api/tickets/${ticketId}/messages`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ text, sender_role: senderRole, attachment_url: attachmentUrl, attachment_type: attachmentType }),
        });
    },

    // ========== Announcements ==========
    getAnnouncements: async (): Promise<Announcement[]> => {
        return request<Announcement[]>("/api/announcements");
    },

    createAnnouncement: async (title: string, message: string, attachments: { url: string, type: string }[], token: string): Promise<Announcement> => {
        return request<Announcement>("/api/announcements", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ title, content: message, attachments }),
        });
    },
};
