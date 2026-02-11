export interface User {
    id: string;
    username: string;
    email?: string;
    full_name?: string;
    role: 'ADMIN' | 'CANDIDATE';
    is_active?: boolean;
}

export interface CandidateData {
    id: string;
    name: string;
    full_name?: string;
    username: string;
    phone?: string;
    bot_name?: string;
    bot_token?: string;
    city?: string;
    province?: string;
    constituency?: string;
    is_active?: boolean;
    vote_count?: number;
    created_at_jalali?: string;
    slogan?: string;
    bio?: string;
    image_url?: string;
    resume?: string;
    ideas?: string;
    address?: string;
    voice_url?: string;
    socials?: any;
    bot_config?: any;
    active_plan_id?: string;
    plan_start_date?: string;
    plan_expires_at?: string;
}

export interface Plan {
    id: string;
    title: string;
    price: string;
    description: string;
    features: string[];
    color: string;
    is_visible: boolean;
    created_at_jalali?: string;
}

export interface Ticket {
    id: string;
    subject: string;
    status: 'OPEN' | 'CLOSED' | 'ANSWERED';
    lastUpdate: number;
    user_id: string;
    userName?: string;
    messages: TicketMessage[];
}

export interface TicketMessage {
    id: string;
    senderId: string;
    senderRole: 'ADMIN' | 'CANDIDATE';
    text: string;
    timestamp: number;
    attachmentUrl?: string;
    attachmentType?: 'IMAGE' | 'VIDEO' | 'VOICE' | 'FILE';
}

export interface Announcement {
    id: string;
    title: string;
    content: string;
    created_at: string;
    attachments?: { url: string; type: 'IMAGE' | 'VIDEO' | 'VOICE' | 'FILE' }[];
}

export type FeedbackStatus = 'NEW' | 'REVIEWED';

export type QuestionStatus = 'PENDING' | 'ANSWERED' | 'REJECTED';

export interface QuestionSubmission {
    id: string;
    candidate_id: string;
    text: string;
    created_at: string;
    topic?: string | null;
    constituency?: string;
    status: QuestionStatus;
    answer_text?: string | null;
    answered_at?: string | null;
    is_public?: boolean;
    is_featured?: boolean;
}

export interface FeedbackSubmission {
    id: string;
    candidate_id: string;
    text: string;
    created_at: string;
    constituency?: string;
    status: FeedbackStatus;
    tag?: string | null;
}

export interface FeedbackTagStat {
    tag: string;
    count: number;
    percent: number;
}

export interface FeedbackStatsResponse {
    days: 7 | 30;
    total: number;
    items: FeedbackTagStat[];
}

export interface AdminDashboardStats {
    active_bots: number;
    total_questions: number;
    total_feedback: number;
    total_bot_requests: number;
}

export interface AdminCandidateStats {
    candidate_id: string;
    total_questions: number;
    total_feedback: number;
    answered_questions: number;
}

export type BotRequestStatus = 'new_request' | 'in_progress' | 'done' | string;

export interface BotRequestSubmission {
    id: string;
    candidate_id: string;
    telegram_user_id: string;
    telegram_username?: string | null;
    requester_full_name?: string | null;
    requester_contact?: string | null;
    role?: string | null;
    constituency?: string | null;
    status: BotRequestStatus;
    text: string;
    created_at: string;
}
