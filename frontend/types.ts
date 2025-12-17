export type Role = 'ADMIN' | 'CANDIDATE';

export interface User {
  id: string;
  username: string;
  role: Role;
  name: string;
}

export interface CandidateData {
  id: string;
  name: string;
  username: string;
  password?: string; // Only for updates
  botName: string;
  botToken: string;
  city: string;
  province: string;
  isActive: boolean;
  userCount: number;
  
  // Profile Data
  slogan?: string;
  resume?: string;
  address?: string;
  ideas?: string;
  photoUrl?: string;
  voiceUrl?: string;

  // Social Media
  socials?: {
    telegramChannel?: string;
    telegramGroup?: string;
    instagram?: string;
  };

  // Bot Advanced Settings
  botConfig?: {
    groupLockEnabled: boolean;
    lockStartTime?: string; // e.g. "23:00"
    lockEndTime?: string;   // e.g. "07:00"
    blockLinks: boolean;
    badWords: string[]; // List of banned words
  };
}

export interface DashboardStats {
  totalCandidates: number;
  activeCandidates: number;
  totalBots: number; // Usually equal to total candidates in this model
  activeBots: number;
  totalUsers: number;
}

// --- NEW TYPES ---

export interface Plan {
  id: string;
  title: string;
  price: string; // e.g., "۵۰۰,۰۰۰ تومان"
  features: string[];
  isVisible: boolean; // Hidden/Visible toggle
  color: string; // Hex Code e.g. #3b82f6
}

export type TicketStatus = 'OPEN' | 'ANSWERED' | 'CLOSED';

export interface TicketMessage {
  id: string;
  senderId: string;
  senderRole: Role;
  text: string;
  timestamp: number;
  attachmentName?: string; // e.g. "image.png"
  attachmentType?: 'IMAGE' | 'FILE';
}

export interface Ticket {
  id: string;
  candidateId: string;
  candidateName: string; // Denormalized for easier display
  subject: string;
  status: TicketStatus;
  messages: TicketMessage[];
  lastUpdate: number;
}