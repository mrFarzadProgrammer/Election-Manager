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


// --- Admin MVP Learning Panel ---

export interface MvpOverviewCounters {
    total_users: number;
    active_users: number;
    total_questions: number;
    answered_questions: number;
    total_comments: number;
    total_commitments: number;
    total_leads: number;
}

export interface MvpRepresentativeOverview {
    candidate_id: number;
    name?: string | null;
    counters: MvpOverviewCounters;
}

export interface MvpOverviewResponse {
    global_counters: MvpOverviewCounters;
    per_candidate: MvpRepresentativeOverview[];
}

export interface BehaviorCounterItem {
    event: string;
    count: number;
}

export interface BehaviorStatsResponse {
    candidate_id?: number | null;
    items: BehaviorCounterItem[];
}

export interface FlowPathItem {
    path: string;
    count: number;
}

export interface FlowPathsResponse {
    candidate_id?: number | null;
    items: FlowPathItem[];
}

export interface QuestionLearningItem {
    question_id: number;
    user_id: string;
    representative_id: number;
    category?: string | null;
    question_text: string;
    status: string;
    created_at: string;
    answered_at?: string | null;
    answer_views_count: number;
    channel_click_count: number;
}

export interface CommitmentLearningItem {
    commitment_id: number;
    representative_id: number;
    title: string;
    body: string;
    created_at: string;
    view_count: number;
}

// ===== Commitments (Public Digital Contracts) =====

export type CommitmentStatus = 'draft' | 'active' | 'in_progress' | 'completed' | 'failed';
export type CommitmentCategory = 'economy' | 'housing' | 'transparency' | 'employment' | 'other';

export interface CommitmentProgressLog {
    id: number;
    note: string;
    created_at: string;
}

export interface Commitment {
    id: number;
    title: string;
    description: string;
    category?: string | null;
    created_by: number;
    created_at: string;
    published_at?: string | null;
    status: CommitmentStatus;
    status_updated_at: string;
    is_locked: boolean;
    progress_logs: CommitmentProgressLog[];
}

export interface CommitmentTermsAcceptance {
    id: string;
    representative_id: number;
    accepted_at: string;
    ip_address?: string | null;
    user_agent?: string | null;
    version: 'v1' | string;
}

export interface LeadItem {
    lead_id: number;
    created_at: string;
    representative_id: number;
    user_id: string;
    username?: string | null;
    selected_role?: string | null;
    phone?: string | null;
}

export interface UxLogItem {
    id: number;
    representative_id: number;
    user_id: string;
    state?: string | null;
    action: string;
    expected_action?: string | null;
    timestamp: string;
}

export interface GlobalBotUserItem {
    user_id: string;
    username?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    phone?: string | null;
    platform: string;
    representative_id: number;
    bot_id?: string | null;
    first_interaction_at: string;
    last_interaction_at: string;
    total_interactions: number;
    asked_question: boolean;
    left_comment: boolean;
    viewed_commitment: boolean;
    became_lead: boolean;
    selected_role?: string | null;
}

// ===== Monitoring (Minimal) =====

export interface TechnicalErrorItem {
    error_id: number;
    timestamp: string;
    service_name: string;
    error_type: string;
    error_message: string;
    user_id?: string | null;
    representative_id?: number | null;
    state?: string | null;
}

export interface MonitoringUxLogItem {
    log_id: number;
    timestamp: string;
    user_id: string;
    representative_id: number;
    current_state?: string | null;
    action: string;
    expected_action?: string | null;
}

export interface HealthCheckItem {
    id: number;
    timestamp: string;
    representative_id?: number | null;
    check_type: string;
    status: 'ok' | 'failed' | string;
}

export interface FlowDropItem {
    id: number;
    representative_id?: number | null;
    flow_type: string;
    started_count: number;
    completed_count: number;
    abandoned_count: number;
    updated_at: string;
}
