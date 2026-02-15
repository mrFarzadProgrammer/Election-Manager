import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import { CandidateData, Plan, Ticket, Announcement } from '../../types';
import {
    Bell,
    CreditCard,
    FileText,
    HelpCircle,
    Lock,
    LogOut,
    MapPin,
    Menu,
    MessageSquare,
    Mic,
    Settings,
    User,
    Users,
    ListChecks,
} from 'lucide-react';
import RepresentativeProfileV1 from './v1/RepresentativeProfileV1';
import VoiceIntroV1 from './v1/VoiceIntroV1';
import StructuredResumeV1 from './v1/StructuredResumeV1';
import FixedProgramsV1 from './v1/FixedProgramsV1';
import OfficesV1 from './v1/OfficesV1';
import PublicFeedbackV1 from './v1/PublicFeedbackV1';
import PublicQuestionsV1 from './v1/PublicQuestionsV1';
import CommitmentsV1 from './v1/CommitmentsV1';
import LockedFeatureNotice from './v1/LockedFeatureNotice';
import ResultModal from './ui/ResultModal';

interface CandidatePanelProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
    plans: Plan[];
    tickets: Ticket[];
    setTickets: React.Dispatch<React.SetStateAction<Ticket[]>>;
    onLogout: () => void;
}

const CandidatePanel: React.FC<CandidatePanelProps> = ({ candidate, onUpdate, plans, tickets, setTickets, onLogout }) => {
    const [activeTab, setActiveTab] = useState<'PROFILE' | 'VOICE' | 'RESUME' | 'PROGRAMS' | 'OFFICES' | 'COMMITMENTS' | 'PUBLIC_MESSAGES' | 'PUBLIC_QUESTIONS' | 'BOT_SETTINGS' | 'PLANS' | 'TICKETS' | 'NOTIFICATIONS'>('PROFILE');
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [panelModal, setPanelModal] = useState<null | { variant: 'info' | 'warning' | 'error' | 'success'; title: string; message: string }>(null);
    const [readTicketTimes, setReadTicketTimes] = useState<{ [key: string]: number }>(() => {
        const saved = localStorage.getItem('read_ticket_times');
        if (!saved) return {};
        try {
            return JSON.parse(saved) || {};
        } catch {
            try {
                localStorage.removeItem('read_ticket_times');
            } catch {
                // ignore
            }
            return {};
        }
    });

    const handleTicketOpen = (ticketId: string) => {
        // Find the ticket to get its lastUpdate time
        const ticket = tickets.find(t => t.id === ticketId);
        const ticketTime = ticket ? ticket.lastUpdate : 0;

        setReadTicketTimes(prev => {
            // Ensure read time is at least 1ms after the ticket's last update
            // This prevents issues where server time > client time
            const effectiveReadTime = Math.max(Date.now(), ticketTime + 1);

            const newState = { ...prev, [ticketId]: effectiveReadTime };
            localStorage.setItem('read_ticket_times', JSON.stringify(newState));
            return newState;
        });
    };

    useEffect(() => {
        api.getAnnouncements().then(setAnnouncements).catch(console.error);
    }, []);

    const myTickets = useMemo(() => tickets.filter(t => t.user_id === candidate.id).sort((a, b) => b.lastUpdate - a.lastUpdate), [tickets, candidate.id]);
    const unreadCount = useMemo(() => myTickets.filter(t => {
        if (t.status !== 'ANSWERED') return false;
        const lastRead = readTicketTimes[t.id] || 0;
        return t.lastUpdate > lastRead;
    }).length, [myTickets, readTicketTimes]);

    const lockedTabs = useMemo(() => new Set(['BOT_SETTINGS', 'PLANS', 'TICKETS', 'NOTIFICATIONS']), []);

    const trySetTab = (tab: typeof activeTab) => {
        if (lockedTabs.has(tab)) {
            setPanelModal({
                variant: 'warning',
                title: 'این بخش قفل است',
                message: 'این بخش در نسخه فعلی قفل است.',
            });
            return;
        }
        setActiveTab(tab);
        setIsMobileMenuOpen(false);
    };

    useEffect(() => {
        if (lockedTabs.has(activeTab)) {
            setActiveTab('PROFILE');
        }
    }, [activeTab, lockedTabs]);

    return (
        <div className='flex relative bg-gray-50 min-h-screen min-h-[100dvh] h-screen h-[100dvh] overflow-hidden'>
            <ResultModal
                open={!!panelModal}
                variant={panelModal?.variant || 'info'}
                title={panelModal?.title || ''}
                message={panelModal?.message || ''}
                onClose={() => setPanelModal(null)}
            />

            <ResultModal
                open={isUploading}
                variant="info"
                title="در حال آپلود"
                message="لطفاً چند لحظه صبر کنید..."
                dismissable={false}
                hideCloseIcon
                onClose={() => setIsUploading(false)}
            />
            <aside className={`fixed lg:static inset-y-0 right-0 z-30 w-64 bg-gray-50 transform transition-transform duration-300 ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'} pt-0 pr-0 pb-4 pl-0`}>
                <div className='flex flex-col h-full bg-white rounded-bl-3xl shadow-sm border-l border-b border-gray-200 overflow-hidden'>
                    <div className='p-6 border-b flex items-center gap-3'>
                        <div className='p-2 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-200'>
                            <FileText size={24} />
                        </div>
                        <h2 className='font-bold text-gray-800 text-sm'>سامانه جامع انتخابات</h2>
                    </div>
                    <nav className='flex-1 p-4 space-y-2 overflow-y-auto custom-scrollbar'>
                        <button onClick={() => trySetTab('PROFILE')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PROFILE' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><User size={20} /> پروفایل نماینده</button>
                        <button onClick={() => trySetTab('VOICE')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'VOICE' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><Mic size={20} /> معرفی صوتی</button>
                        <button onClick={() => trySetTab('RESUME')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'RESUME' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><FileText size={20} /> سوابق</button>
                        <button onClick={() => trySetTab('PROGRAMS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PROGRAMS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><ListChecks size={20} /> برنامه‌ها</button>
                        <button onClick={() => trySetTab('OFFICES')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'OFFICES' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><MapPin size={20} /> ستادها</button>
                        <button onClick={() => trySetTab('COMMITMENTS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'COMMITMENTS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><FileText size={20} /> تعهدات</button>
                        <button onClick={() => trySetTab('PUBLIC_MESSAGES')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PUBLIC_MESSAGES' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><Users size={20} /> نظرات و دغدغه‌ها</button>
                        <button onClick={() => trySetTab('PUBLIC_QUESTIONS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PUBLIC_QUESTIONS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><HelpCircle size={20} /> سؤال‌های مردمی</button>

                        <div className='pt-3 border-t border-gray-100' />

                        <button
                            onClick={() => trySetTab('BOT_SETTINGS')}
                            disabled
                            className='w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-gray-400 bg-gray-50 cursor-not-allowed'
                            title='این بخش در نسخه فعلی قفل است'
                        >
                            <span className='flex items-center gap-3'><Settings size={20} /> تنظیمات بات</span>
                            <Lock size={16} />
                        </button>

                        <button
                            onClick={() => trySetTab('PLANS')}
                            disabled
                            className='w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-gray-400 bg-gray-50 cursor-not-allowed'
                            title='این بخش در نسخه فعلی قفل است'
                        >
                            <span className='flex items-center gap-3'><CreditCard size={20} /> لیست پلن‌ها</span>
                            <Lock size={16} />
                        </button>

                        <button
                            onClick={() => trySetTab('TICKETS')}
                            disabled
                            className='w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-gray-400 bg-gray-50 cursor-not-allowed'
                            title='این بخش در نسخه فعلی قفل است'
                        >
                            <span className='flex items-center gap-3'>
                                <span className="relative">
                                    <MessageSquare size={20} />
                                    {unreadCount > 0 && (
                                        <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] w-4 h-4 flex items-center justify-center rounded-full">
                                            {unreadCount}
                                        </span>
                                    )}
                                </span>
                                پشتیبانی
                            </span>
                            <Lock size={16} />
                        </button>

                        <button
                            onClick={() => trySetTab('NOTIFICATIONS')}
                            disabled
                            className='w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-gray-400 bg-gray-50 cursor-not-allowed'
                            title='این بخش در نسخه فعلی قفل است'
                        >
                            <span className='flex items-center gap-3'><Bell size={20} /> اطلاعیه‌ها</span>
                            <Lock size={16} />
                        </button>
                    </nav>
                    <div className="px-4 mb-4 mt-auto">
                        <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-bold text-blue-800">پلن فعال: پایه</span>
                            </div>
                            <div className="text-[10px] text-blue-600">
                                اعتبار: ۳۹ روز
                            </div>
                        </div>
                    </div>
                </div>
            </aside>
            <main className='flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden'>
                <header className='bg-white shadow-sm border-b px-4 sm:px-6 py-3 flex items-center justify-between'>
                    <button className='lg:hidden' onClick={() => setIsMobileMenuOpen(true)}><Menu size={24} /></button>

                    {/* User Profile Card (Left Side) */}
                    <div className='mr-auto flex items-center gap-4'>
                        <button onClick={onLogout} className='text-gray-400 hover:text-red-500 transition-colors'>
                            <LogOut size={20} className="transform rotate-180" />
                        </button>
                        <div className='bg-gray-50 rounded-full pl-1 pr-4 py-1 flex items-center gap-3 border border-gray-100'>
                            <div className='text-left'>
                                <p className='text-sm font-bold text-gray-800'>{candidate.name}</p>
                                <p className='text-[10px] text-gray-500'>نامزد انتخاباتی</p>
                            </div>
                            <div className='w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600'>
                                <User size={16} />
                            </div>
                        </div>
                    </div>
                </header>
                <div className='flex-1 min-h-0 overflow-hidden p-2 sm:p-3 lg:p-4 flex flex-col'>
                    <div className='w-full h-full flex flex-col'>
                        <div className="h-full overflow-y-auto pr-2 custom-scrollbar">
                            {activeTab === 'PROFILE' && <RepresentativeProfileV1 candidate={candidate} onUpdate={onUpdate} />}
                            {activeTab === 'VOICE' && <VoiceIntroV1 candidate={candidate} onUpdate={onUpdate} />}
                            {activeTab === 'RESUME' && <StructuredResumeV1 candidate={candidate} onUpdate={onUpdate} />}
                            {activeTab === 'PROGRAMS' && <FixedProgramsV1 candidate={candidate} onUpdate={onUpdate} />}
                            {activeTab === 'OFFICES' && <OfficesV1 candidate={candidate} onUpdate={onUpdate} />}
                            {activeTab === 'COMMITMENTS' && <CommitmentsV1 candidate={candidate} />}
                            {activeTab === 'PUBLIC_MESSAGES' && <PublicFeedbackV1 candidate={candidate} />}
                            {activeTab === 'PUBLIC_QUESTIONS' && <PublicQuestionsV1 candidate={candidate} />}
                            {lockedTabs.has(activeTab) && <LockedFeatureNotice />}
                        </div>
                    </div>
                </div>
            </main>
            {isMobileMenuOpen && <div className='fixed inset-0 bg-black/50 z-20 lg:hidden' onClick={() => setIsMobileMenuOpen(false)} />}
        </div>
    );
};

export default CandidatePanel;
