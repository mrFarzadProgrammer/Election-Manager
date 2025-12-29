import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { CandidateData, Plan, Ticket, Announcement } from '../../types';
import { Users, CreditCard, MessageSquare, Megaphone, LogOut, LayoutDashboard, Menu } from 'lucide-react';
import CandidatesTab from './CandidatesTab';
import PlansTab from './PlansTab';
import TicketsTab from './TicketsTab';
import AnnouncementsTab from './AnnouncementsTab';

interface AdminPanelProps {
    candidates: CandidateData[];
    setCandidates: React.Dispatch<React.SetStateAction<CandidateData[]>>;
    plans: Plan[];
    setPlans: React.Dispatch<React.SetStateAction<Plan[]>>;
    tickets: Ticket[];
    setTickets: React.Dispatch<React.SetStateAction<Ticket[]>>;
    onLogout: () => void;
}

const AdminPanel: React.FC<AdminPanelProps> = ({ candidates, setCandidates, plans, setPlans, tickets, setTickets, onLogout }) => {
    const [activeTab, setActiveTab] = useState<'CANDIDATES' | 'PLANS' | 'TICKETS' | 'ANNOUNCEMENTS'>('CANDIDATES');
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        api.getAnnouncements().then(setAnnouncements).catch(console.error);
    }, []);

    const handleToggleStatus = async (id: string, currentStatus: boolean) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        await api.updateCandidateStatus(id, !currentStatus, token);
        setCandidates(prev => prev.map(c => c.id === id ? { ...c, is_active: !currentStatus } : c));
    };

    const handleDeleteCandidate = async (id: string) => {
        if (!window.confirm('حذف کاندیدا؟')) return;
        const token = localStorage.getItem('access_token');
        if (!token) return;
        await api.deleteCandidate(id, token);
        setCandidates(prev => prev.filter(c => c.id !== id));
    };

    const handleSavePlan = async (planData: Partial<Plan>) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        if (planData.id) { alert('ویرایش پلن نمایشی است'); }
        else { const newPlan = await api.createPlan(planData as any, token); setPlans(prev => [...prev, newPlan]); }
    };

    const handleDeletePlan = async (id: string) => {
        if (!window.confirm('حذف پلن؟')) return;
        const token = localStorage.getItem('access_token');
        if (!token) return;
        await api.deletePlan(id, token);
        setPlans(prev => prev.filter(p => p.id !== id));
    };

    const handleTicketReply = async (ticketId: string, message: string, attachment?: File) => {
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
            const newMsg = await api.addTicketMessage(ticketId, message || (attachment ? '[فایل]' : ''), 'ADMIN', token, attachmentUrl, attachmentType as any);
            setTickets(prev => prev.map(t => t.id === ticketId ? { ...t, lastUpdate: Date.now(), messages: [...t.messages, { id: newMsg.id.toString(), senderId: 'admin', senderRole: 'ADMIN', text: newMsg.text, timestamp: Date.now(), attachmentUrl }] } : t));
        } finally { setIsUploading(false); }
    };

    const handleSendAnnouncement = async (title: string, message: string, file?: File) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        setIsUploading(true);
        try {
            let imageUrl = undefined;
            if (file) {
                const formData = new FormData(); formData.append('file', file);
                const res = await fetch('http://localhost:8000/api/upload', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData });
                const data = await res.json(); imageUrl = data.url;
            }
            const newAnn = await api.createAnnouncement(title, message, imageUrl, token);
            setAnnouncements(prev => [newAnn, ...prev]);
        } finally { setIsUploading(false); }
    };

    const navItems = [
        { id: 'CANDIDATES', label: 'کاندیداها', icon: <Users size={20} /> },
        { id: 'PLANS', label: 'پلن‌ها', icon: <CreditCard size={20} /> },
        { id: 'TICKETS', label: 'پشتیبانی', icon: <MessageSquare size={20} /> },
        { id: 'ANNOUNCEMENTS', label: 'اطلاعیه‌ها', icon: <Megaphone size={20} /> },
    ];

    return (
        <div className='flex h-screen bg-gray-50 overflow-hidden'>
            {isUploading && <div className='fixed inset-0 bg-black/50 z-[60] flex items-center justify-center'><div className='bg-white p-6 rounded-2xl'>در حال آپلود...</div></div>}
            <aside className={`fixed lg:static inset-y-0 right-0 z-30 w-64 bg-white shadow-lg transform transition-transform duration-300 ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}`}>
                <div className='flex flex-col h-full'>
                    <div className='p-6 border-b flex items-center gap-3'><LayoutDashboard size={24} className='text-blue-600' /><h1 className='font-bold text-xl'>پنل مدیریت</h1></div>
                    <nav className='flex-1 p-4 space-y-2'>
                        {navItems.map(item => (
                            <button key={item.id} onClick={() => { setActiveTab(item.id as any); setIsMobileMenuOpen(false); }} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === item.id ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-600 hover:bg-gray-100'}`}>{item.icon}<span>{item.label}</span></button>
                        ))}
                    </nav>
                    <div className='p-4 border-t'><button onClick={onLogout} className='flex items-center gap-3 w-full p-3 text-red-600 hover:bg-red-50 rounded-xl'><LogOut size={20} /><span>خروج</span></button></div>
                </div>
            </aside>
            <main className='flex-1 flex flex-col min-w-0 overflow-hidden'>
                <header className='bg-white shadow-sm border-b px-6 py-4 flex items-center justify-between lg:hidden'><button onClick={() => setIsMobileMenuOpen(true)}><Menu size={24} /></button><span>پنل مدیریت</span></header>
                <div className='flex-1 overflow-y-auto p-4 lg:p-8'>
                    <div className='max-w-6xl mx-auto'>
                        {activeTab === 'CANDIDATES' && <CandidatesTab candidates={candidates} searchQuery={searchQuery} setSearchQuery={setSearchQuery} onEdit={() => { }} onDelete={handleDeleteCandidate} onToggleStatus={handleToggleStatus} />}
                        {activeTab === 'PLANS' && <PlansTab plans={plans} onSavePlan={handleSavePlan} onDeletePlan={handleDeletePlan} />}
                        {activeTab === 'TICKETS' && <TicketsTab tickets={tickets} onReply={handleTicketReply} onCloseTicket={() => { }} isUploading={isUploading} />}
                        {activeTab === 'ANNOUNCEMENTS' && <AnnouncementsTab announcements={announcements} onSendAnnouncement={handleSendAnnouncement} onDeleteAnnouncement={() => { }} isUploading={isUploading} />}
                    </div>
                </div>
            </main>
            {isMobileMenuOpen && <div className='fixed inset-0 bg-black/50 z-20 lg:hidden' onClick={() => setIsMobileMenuOpen(false)} />}
        </div>
    );
};

export default AdminPanel;
