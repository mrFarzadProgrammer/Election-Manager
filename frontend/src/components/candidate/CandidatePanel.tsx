import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { CandidateData, Plan, Ticket, Announcement } from '../../types';
import { FileText, CreditCard, MessageSquare, Bell, LogOut, User, Menu, X, LayoutDashboard, Image, Settings, List } from 'lucide-react';
import ProfileTab from './ProfileTab';
import PlansTab from './PlansTab';
import TicketsTab from './TicketsTab';
import AnnouncementsTab from './AnnouncementsTab';
import InfoStatsTab from './InfoStatsTab';
import MediaTab from './MediaTab';
import MyProgramsTab from './MyProgramsTab';

interface CandidatePanelProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => void;
    plans: Plan[];
    tickets: Ticket[];
    setTickets: React.Dispatch<React.SetStateAction<Ticket[]>>;
    onLogout: () => void;
}

const CandidatePanel: React.FC<CandidatePanelProps> = ({ candidate, onUpdate, plans, tickets, setTickets, onLogout }) => {
    const [activeTab, setActiveTab] = useState<'INFO_STATS' | 'MEDIA' | 'MY_PLANS' | 'BOT_SETTINGS' | 'PLANS' | 'TICKETS' | 'NOTIFICATIONS'>('INFO_STATS');
    const [formData, setFormData] = useState<CandidateData>(candidate);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
    const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

    useEffect(() => {
        api.getAnnouncements().then(setAnnouncements).catch(console.error);
    }, []);

    const handleSaveProfile = () => { onUpdate(formData); alert('ذخیره شد.'); };
    const handleChange = (field: keyof CandidateData, value: string) => setFormData(prev => ({ ...prev, [field]: value }));

    const handleCreateTicket = async (subject: string, message: string) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        const created = await api.createTicket(subject, message, token);
        const newTicket: Ticket = { id: created.id.toString(), userId: candidate.id, userName: candidate.name, subject: created.subject, status: created.status as any, lastUpdate: Date.now(), messages: (created.messages || []).map((m: any) => ({ id: m.id.toString(), senderId: m.sender_role === 'CANDIDATE' ? candidate.id : 'admin', senderRole: m.sender_role, text: m.text, timestamp: new Date(m.created_at).getTime() })) };
        setTickets(prev => [...prev, newTicket]);
        alert('تیکت ایجاد شد');
    };

    const handleReplyTicket = async (ticketId: string, message: string, attachment?: File) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        setIsUploading(true);
        try {
            let attachmentUrl = undefined;
            let attachmentType = undefined;
            if (attachment) {
                const formData = new FormData(); formData.append('file', attachment);
                const res = await fetch('http://localhost:8000/api/upload', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData });
                const data = await res.json(); attachmentUrl = data.url; attachmentType = attachment.type.startsWith('image/') ? 'IMAGE' : 'FILE';
            }
            const newMsg = await api.addTicketMessage(ticketId, message || (attachment ? '[فایل]' : ''), 'CANDIDATE', token, attachmentUrl, attachmentType as any);
            setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, status: 'OPEN', lastUpdate: Date.now(), messages: [...t.messages, { id: newMsg.id.toString(), senderId: candidate.id, senderRole: 'CANDIDATE', text: newMsg.text, timestamp: Date.now(), attachmentUrl }] } : t));
        } finally { setIsUploading(false); }
    };

    const myTickets = tickets.filter(t => t.userId === candidate.id).sort((a, b) => b.lastUpdate - a.lastUpdate);

    return (
        <div className='flex h-full relative bg-gray-50'>
            {isUploading && <div className='fixed inset-0 bg-black/50 z-[60] flex items-center justify-center'><div className='bg-white p-6 rounded-2xl'>در حال آپلود...</div></div>}
            <aside className={`fixed lg:static inset-y-0 right-0 z-30 w-64 bg-gray-50 transform transition-transform duration-300 ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'} pt-0 pr-0 pb-4 pl-0`}>
                <div className='flex flex-col h-full bg-white rounded-bl-3xl shadow-sm border-l border-b border-gray-200 overflow-hidden'>
                    <div className='p-6 border-b flex items-center gap-3'>
                        <div className='p-2 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-200'>
                            <FileText size={24} />
                        </div>
                        <h2 className='font-bold text-gray-800 text-sm'>سامانه جامع انتخابات</h2>
                    </div>
                    <nav className='flex-1 p-4 space-y-2 overflow-y-auto custom-scrollbar'>
                        <button onClick={() => setActiveTab('INFO_STATS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'INFO_STATS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><LayoutDashboard size={20} /> اطلاعات و آمار</button>
                        <button onClick={() => setActiveTab('MEDIA')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'MEDIA' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><Image size={20} /> رسانه و فایل</button>
                        <button onClick={() => setActiveTab('MY_PLANS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'MY_PLANS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><List size={20} /> برنامه‌های من</button>
                        <button onClick={() => setActiveTab('BOT_SETTINGS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'BOT_SETTINGS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><Settings size={20} /> تنظیمات بات</button>
                        <button onClick={() => setActiveTab('PLANS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PLANS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><CreditCard size={20} /> لیست پلن‌ها</button>
                        <button onClick={() => setActiveTab('TICKETS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'TICKETS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><MessageSquare size={20} /> پشتیبانی</button>
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
            <main className='flex-1 flex flex-col min-w-0 overflow-hidden h-screen'>
                <header className='bg-white shadow-sm border-b px-6 py-3 flex items-center justify-between'>
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
                <div className='flex-1 overflow-hidden p-2 lg:p-4 flex flex-col'>
                    <div className='w-full h-full flex flex-col'>
                        {activeTab === 'INFO_STATS' ? (
                            <InfoStatsTab candidate={candidate} onUpdate={onUpdate} />
                        ) : activeTab === 'MEDIA' ? (
                            <MediaTab candidate={candidate} onUpdate={onUpdate} />
                        ) : activeTab === 'MY_PLANS' ? (
                            <MyProgramsTab candidate={candidate} onUpdate={onUpdate} />
                        ) : (
                            <div className="h-full overflow-y-auto pr-2 custom-scrollbar">
                                {activeTab === 'BOT_SETTINGS' && <ProfileTab formData={formData} handleChange={handleChange} onSave={handleSaveProfile} />}
                                {activeTab === 'PLANS' && <PlansTab plans={plans} onSelectPlan={(p) => { setSelectedPlan(p); setShowSubscriptionModal(true); }} />}
                                {activeTab === 'TICKETS' && <TicketsTab tickets={myTickets} onCreateTicket={handleCreateTicket} onReplyTicket={handleReplyTicket} isUploading={isUploading} />}
                                {activeTab === 'NOTIFICATIONS' && <AnnouncementsTab announcements={announcements} />}
                            </div>
                        )}
                    </div>
                </div>
            </main>
            {showSubscriptionModal && (
                <div className='fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4'>
                    <div className='bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl relative'>
                        <button onClick={() => setShowSubscriptionModal(false)} className='absolute top-4 left-4 text-gray-400'><X size={24} /></button>
                        <h3 className='text-xl font-bold text-center mb-4'>خرید اشتراک {selectedPlan?.title}</h3>
                        <p className='text-center mb-6'>لطفاً مبلغ {selectedPlan?.price ? Number(selectedPlan.price).toLocaleString('fa-IR') : ''} تومان را واریز کنید.</p>
                        <div className='bg-gray-50 p-4 rounded-xl text-center mb-6 font-mono text-xl font-bold'>6104 3389 6232 1390</div>
                        <button onClick={() => { setShowSubscriptionModal(false); setActiveTab('TICKETS'); handleCreateTicket(`فیش واریز - ${selectedPlan?.title}`, 'تصویر فیش پیوست شد.'); }} className='w-full py-3 bg-blue-600 text-white rounded-xl'>ارسال فیش واریز</button>
                    </div>
                </div>
            )}
            {isMobileMenuOpen && <div className='fixed inset-0 bg-black/50 z-20 lg:hidden' onClick={() => setIsMobileMenuOpen(false)} />}
        </div>
    );
};

export default CandidatePanel;
