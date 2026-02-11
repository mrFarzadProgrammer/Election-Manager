import { User, CandidateData as Candidate, Plan, Ticket, Announcement, FeedbackSubmission, FeedbackStatsResponse, QuestionSubmission, BotRequestSubmission, AdminDashboardStats } from "../types";

const VITE_API_BASE =
    (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_URL) ||
    undefined;

export const API_BASE =
    VITE_API_BASE ||
    (typeof process !== "undefined" && (process as any).env?.REACT_APP_API_BASE_URL) ||
    "http://127.0.0.1:8000";

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

const refreshAccessToken = async (): Promise<RefreshResponse | null> => {
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

    let res: Response;
    try {
        res = await fetch(url, options);
    } catch (e: any) {
        throw new Error("ارتباط با سرور برقرار نشد. لطفاً اتصال یا اجرای سرور را بررسی کنید.");
    }

    if (!res.ok) {
        // If access token expired, try refreshing once and retry the original request.
        if (res.status === 401 && !_retried && hasAuthorizationHeader(options.headers)) {
            const refreshed = await refreshAccessToken();
            if (refreshed?.access_token) {
                const nextHeaders = setAuthorizationHeader(options.headers, `Bearer ${refreshed.access_token}`);
                return request<T>(path, { ...options, headers: nextHeaders }, true);
            }

            // Refresh failed: treat as expired session.
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
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

    getMe: async (token: string): Promise<User> => {
        const user = await request<any>("/api/auth/me", {
            method: "GET",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        return { ...user, id: String(user.id) };
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

    getCandidates: async (): Promise<Candidate[]> => {
        try {
            const data = await request<any[]>("/api/candidates");
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
