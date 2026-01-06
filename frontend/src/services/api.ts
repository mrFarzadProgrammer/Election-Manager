import { User, CandidateData as Candidate, Plan, Ticket, Announcement } from "../types";

const API_BASE =
    (typeof process !== "undefined" && (process as any).env?.REACT_APP_API_BASE_URL) ||
    "http://localhost:8000";

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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

    let res: Response;
    try {
        res = await fetch(url, options);
    } catch (e: any) {
        throw new Error("ارتباط با سرور برقرار نشد. لطفاً اتصال یا اجرای سرور را بررسی کنید.");
    }

    if (!res.ok) {
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
