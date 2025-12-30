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
}

export interface Plan {
    id: string;
    title: string;
    price: string;
    description: string;
    features: string[];
    color: string;
    is_visible: boolean;
}

export interface Ticket {
    id: string;
    subject: string;
    status: 'OPEN' | 'CLOSED' | 'ANSWERED';
    lastUpdate: number;
    user_id: string;
    messages: TicketMessage[];
}

export interface TicketMessage {
    id: string;
    senderId: string;
    senderRole: 'ADMIN' | 'CANDIDATE';
    text: string;
    timestamp: number;
    attachmentUrl?: string;
}

export interface Announcement {
    id: string;
    title: string;
    message: string;
    date: string;
    imageUrl?: string;
}
