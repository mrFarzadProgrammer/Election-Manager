import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { CandidateData, Plan, Ticket, Announcement } from '../../types';
import { FileText, CreditCard, MessageSquare, Bell, LogOut, User, Menu, X } from 'lucide-react';
import ProfileTab from './ProfileTab';
import PlansTab from './PlansTab';
import TicketsTab from './TicketsTab';
import AnnouncementsTab from './AnnouncementsTab';

interface CandidatePanelProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => void;
    plans: Plan[];
    tickets: Ticket[];
    setTickets: React.Dispatch<React.SetStateAction<Ticket[]>>;
    onLogout: () => void;
}

const CandidatePanel: React.FC<CandidatePanelProps> = ({ candidate, onUpdate, plans, tickets, setTickets, onLogout }) => {
    const [activeTab, setActiveTab] = useState<'PROFILE' | 'PLANS' | 'TICKETS' | 'NOTIFICATIONS'>('PROFILE');
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
            <aside className={`fixed lg:static inset-y-0 right-0 z-30 w-64 bg-white shadow-lg transform transition-transform duration-300 ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}`}>
                <div className='flex flex-col h-full'>
                    <div className='p-6 border-b flex items-center gap-3'><div className='p-2 bg-blue-50 rounded-lg text-blue-600'><User size={24} /></div><h2 className='font-bold text-gray-800'>داشبورد کاندیدا</h2></div>
                    <nav className='flex-1 p-4 space-y-2'>
                        <button onClick={() => setActiveTab('PROFILE')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PROFILE' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><FileText size={20} /> اطلاعات</button>
                        <button onClick={() => setActiveTab('PLANS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'PLANS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><CreditCard size={20} /> اشتراک</button>
                        <button onClick={() => setActiveTab('TICKETS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'TICKETS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><MessageSquare size={20} /> پشتیبانی</button>
                        <button onClick={() => setActiveTab('NOTIFICATIONS')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl ${activeTab === 'NOTIFICATIONS' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}><Bell size={20} /> اطلاعیه‌ها</button>
                    </nav>
                    <div className='p-4 border-t'><button onClick={onLogout} className='flex items-center gap-3 w-full p-3 text-red-600 hover:bg-red-50 rounded-xl'><LogOut size={20} /> خروج</button></div>
                </div>
            </aside>
            <main className='flex-1 flex flex-col min-w-0 overflow-hidden h-screen'>
                <header className='bg-white shadow-sm border-b px-6 py-4 flex items-center justify-between'><button className='lg:hidden' onClick={() => setIsMobileMenuOpen(true)}><Menu size={24} /></button><div className='mr-auto'>{candidate.name}</div></header>
                <div className='flex-1 overflow-y-auto p-4 lg:p-8'>
                    <div className='max-w-5xl mx-auto'>
                        {activeTab === 'PROFILE' && <ProfileTab formData={formData} handleChange={handleChange} onSave={handleSaveProfile} />}
                        {activeTab === 'PLANS' && <PlansTab plans={plans} onSelectPlan={(p) => { setSelectedPlan(p); setShowSubscriptionModal(true); }} />}
                        {activeTab === 'TICKETS' && <TicketsTab tickets={myTickets} onCreateTicket={handleCreateTicket} onReplyTicket={handleReplyTicket} isUploading={isUploading} />}
                        {activeTab === 'NOTIFICATIONS' && <AnnouncementsTab announcements={announcements} />}
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
