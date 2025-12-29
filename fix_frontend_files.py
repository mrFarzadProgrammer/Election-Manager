import os

files = {
    "frontend/src/components/admin/CandidatesTab.tsx": """import React from 'react';
import { CandidateData } from '../../types';
import { Search, Edit, Trash2, Bot } from 'lucide-react';

interface CandidatesTabProps {
    candidates: CandidateData[];
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    onEdit: (candidate: CandidateData) => void;
    onDelete: (id: string) => void;
    onToggleStatus: (id: string, currentStatus: boolean) => void;
}

const CandidatesTab: React.FC<CandidatesTabProps> = ({
    candidates,
    searchQuery,
    setSearchQuery,
    onEdit,
    onDelete,
    onToggleStatus
}) => {
    const filteredCandidates = candidates.filter(c =>
        (c.name || '').includes(searchQuery) || (c.username || '').includes(searchQuery)
    );

    return (
        <div className='bg-white rounded-2xl shadow-sm border overflow-hidden'>
            <div className='p-6 border-b flex items-center justify-between gap-4'>
                <h3 className='font-bold text-lg'>لیست کاندیداها</h3>
                <div className='relative w-64'>
                    <Search className='absolute right-3 top-3 text-gray-400' size={18} />
                    <input
                        type='text'
                        placeholder='جستجو...'
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className='w-full pl-4 pr-10 py-2 bg-gray-50 border rounded-xl focus:bg-white transition outline-none'
                    />
                </div>
            </div>
            
            <div className='overflow-x-auto'>
                <table className='w-full'>
                    <thead className='bg-gray-50 text-gray-500 text-sm'>
                        <tr>
                            <th className='p-4 text-right'>نام کاندیدا</th>
                            <th className='p-4 text-right'>نام کاربری</th>
                            <th className='p-4 text-right'>وضعیت ربات</th>
                            <th className='p-4 text-center'>وضعیت حساب</th>
                            <th className='p-4 text-center'>عملیات</th>
                        </tr>
                    </thead>
                    <tbody className='divide-y'>
                        {filteredCandidates.map(candidate => (
                            <tr key={candidate.id} className='hover:bg-gray-50 transition'>
                                <td className='p-4 font-medium'>{candidate.name}</td>
                                <td className='p-4 text-gray-600 dir-ltr text-right'>{candidate.username}</td>
                                <td className='p-4'>
                                    {candidate.bot_name ? (
                                        <span className='flex items-center gap-1 text-blue-600 text-sm bg-blue-50 px-2 py-1 rounded-lg w-fit'>
                                            <Bot size={14} /> @{candidate.bot_name}
                                        </span>
                                    ) : (
                                        <span className='text-gray-400 text-sm'>-</span>
                                    )}
                                </td>
                                <td className='p-4 text-center'>
                                    <button
                                        onClick={() => onToggleStatus(candidate.id, candidate.is_active || false)}
                                        className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                                            candidate.is_active 
                                            ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                                            : 'bg-red-100 text-red-700 hover:bg-red-200'
                                        }`}
                                    >
                                        {candidate.is_active ? 'فعال' : 'غیرفعال'}
                                    </button>
                                </td>
                                <td className='p-4'>
                                    <div className='flex items-center justify-center gap-2'>
                                        <button onClick={() => onEdit(candidate)} className='p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition'>
                                            <Edit size={18} />
                                        </button>
                                        <button onClick={() => onDelete(candidate.id)} className='p-2 text-red-600 hover:bg-red-50 rounded-lg transition'>
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default CandidatesTab;""",

    "frontend/src/components/admin/PlansTab.tsx": """import React, { useState } from 'react';
import { Plan } from '../../types';
import { Plus, Edit, Trash2, Check } from 'lucide-react';

interface PlansTabProps {
    plans: Plan[];
    onSavePlan: (plan: Partial<Plan>) => void;
    onDeletePlan: (id: string) => void;
}

const PlansTab: React.FC<PlansTabProps> = ({ plans, onSavePlan, onDeletePlan }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editingPlan, setEditingPlan] = useState<Partial<Plan>>({});

    const handleEdit = (plan?: Plan) => {
        setEditingPlan(plan || { title: '', price: 0, features: [], color: '#3B82F6' });
        setIsEditing(true);
    };

    const handleSave = () => {
        if (!editingPlan.title || !editingPlan.price) return;
        onSavePlan(editingPlan);
        setIsEditing(false);
        setEditingPlan({});
    };

    if (isEditing) {
        return (
            <div className='bg-white p-6 rounded-2xl shadow-sm border max-w-2xl mx-auto'>
                <h3 className='font-bold text-lg mb-6'>{editingPlan.id ? 'ویرایش پلن' : 'ایجاد پلن جدید'}</h3>
                <div className='space-y-4'>
                    <input
                        placeholder='عنوان پلن'
                        value={editingPlan.title}
                        onChange={e => setEditingPlan({ ...editingPlan, title: e.target.value })}
                        className='w-full border rounded-xl px-4 py-2'
                    />
                    <input
                        placeholder='قیمت (تومان)'
                        value={editingPlan.price ? Number(editingPlan.price).toLocaleString() : ''}
                        onChange={e => {
                            const val = e.target.value.replace(/,/g, '');
                            if (!isNaN(Number(val))) setEditingPlan({ ...editingPlan, price: Number(val) });
                        }}
                        className='w-full border rounded-xl px-4 py-2 dir-ltr text-left'
                    />
                    <textarea
                        placeholder='ویژگی‌ها (هر خط یک ویژگی)'
                        value={editingPlan.features?.join('\\n')}
                        onChange={e => setEditingPlan({ ...editingPlan, features: e.target.value.split('\\n') })}
                        className='w-full border rounded-xl px-4 py-2 h-32'
                    />
                    <div className='flex justify-end gap-3 mt-6'>
                        <button onClick={() => setIsEditing(false)} className='px-6 py-2 text-gray-600 hover:bg-gray-100 rounded-xl'>انصراف</button>
                        <button onClick={handleSave} className='px-6 py-2 bg-blue-600 text-white rounded-xl'>ذخیره</button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className='space-y-6'>
            <div className='flex justify-between items-center'>
                <h3 className='font-bold text-lg'>مدیریت پلن‌های اشتراک</h3>
                <button onClick={() => handleEdit()} className='flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl'>
                    <Plus size={18} /> پلن جدید
                </button>
            </div>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                {plans.map(plan => (
                    <div key={plan.id} className='bg-white p-6 rounded-2xl shadow-sm border relative group'>
                        <div className='absolute top-4 left-4 flex gap-2 opacity-0 group-hover:opacity-100 transition'>
                            <button onClick={() => handleEdit(plan)} className='p-2 bg-blue-50 text-blue-600 rounded-lg'><Edit size={16} /></button>
                            <button onClick={() => onDeletePlan(plan.id)} className='p-2 bg-red-50 text-red-600 rounded-lg'><Trash2 size={16} /></button>
                        </div>
                        <h3 className='text-xl font-bold text-center mb-2'>{plan.title}</h3>
                        <p className='text-center text-2xl font-bold text-blue-600 mb-4'>{Number(plan.price).toLocaleString('fa-IR')} تومان</p>
                        <div className='space-y-2 border-t pt-4'>
                            {plan.features.map((f, i) => (
                                <div key={i} className='flex items-center gap-2 text-sm text-gray-600'><Check size={16} className='text-green-500' />{f}</div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PlansTab;""",

    "frontend/src/components/admin/TicketsTab.tsx": """import React, { useState, useRef } from 'react';
import { Ticket } from '../../types';
import { MessageSquare, Send, Paperclip } from 'lucide-react';

interface TicketsTabProps {
    tickets: Ticket[];
    onReply: (ticketId: string, message: string, attachment?: File) => Promise<void>;
    onCloseTicket: (ticketId: string) => void;
    isUploading: boolean;
}

const TicketsTab: React.FC<TicketsTabProps> = ({ tickets, onReply, onCloseTicket, isUploading }) => {
    const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
    const [replyMsg, setReplyMsg] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const activeTicket = tickets.find(t => t.id === activeTicketId);
    const sortedTickets = [...tickets].sort((a, b) => b.lastUpdate - a.lastUpdate);

    const handleSend = async () => {
        if (!activeTicketId || !replyMsg.trim()) return;
        await onReply(activeTicketId, replyMsg);
        setReplyMsg('');
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !activeTicketId) return;
        await onReply(activeTicketId, '', file);
        e.target.value = '';
    };

    return (
        <div className='flex h-[600px] bg-white rounded-2xl shadow-sm border overflow-hidden'>
            <div className='w-1/3 border-l bg-gray-50 flex flex-col'>
                <div className='p-4 border-b bg-white'><h3 className='font-bold'>تیکت‌های پشتیبانی</h3></div>
                <div className='flex-1 overflow-y-auto'>
                    {sortedTickets.map(ticket => (
                        <div key={ticket.id} onClick={() => setActiveTicketId(ticket.id)} className={`p-4 border-b cursor-pointer hover:bg-gray-100 ${activeTicketId === ticket.id ? 'bg-blue-50 border-r-4 border-r-blue-600' : ''}`}>
                            <div className='flex justify-between items-start mb-1'>
                                <h4 className='font-bold text-sm truncate max-w-[150px]'>{ticket.subject}</h4>
                                <span className='text-[10px] text-gray-400'>{new Date(ticket.lastUpdate).toLocaleDateString('fa-IR')}</span>
                            </div>
                            <p className='text-xs text-gray-500 mb-2'>{ticket.userName}</p>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full ${ticket.status === 'OPEN' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-700'}`}>{ticket.status === 'OPEN' ? 'باز' : 'بسته'}</span>
                        </div>
                    ))}
                </div>
            </div>
            <div className='flex-1 flex flex-col bg-white'>
                {activeTicket ? (
                    <>
                        <div className='p-4 border-b flex justify-between items-center bg-gray-50'>
                            <div><h3 className='font-bold'>{activeTicket.subject}</h3><p className='text-xs text-gray-500'>فرستنده: {activeTicket.userName}</p></div>
                        </div>
                        <div className='flex-1 overflow-y-auto p-4 space-y-4'>
                            {activeTicket.messages.map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.senderRole === 'ADMIN' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[70%] p-3 rounded-2xl ${msg.senderRole === 'ADMIN' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-gray-100 text-gray-800 rounded-bl-none'}`}>
                                        <p className='text-sm'>{msg.text}</p>
                                        {msg.attachmentUrl && <a href={msg.attachmentUrl} target='_blank' className='block mt-2 text-xs bg-white/20 p-2 rounded flex items-center gap-2'><Paperclip size={14} /> دانلود فایل</a>}
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className='p-4 border-t bg-gray-50 flex gap-2 items-center'>
                            <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className='p-2 text-gray-500 hover:bg-gray-200 rounded-full'><Paperclip size={20} /></button>
                            <input type='file' ref={fileInputRef} className='hidden' onChange={handleFileUpload} />
                            <input className='flex-1 border rounded-xl px-4 py-2' placeholder='پاسخ...' value={replyMsg} onChange={(e) => setReplyMsg(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleSend()} disabled={isUploading} />
                            <button onClick={handleSend} disabled={isUploading} className='p-2 bg-blue-600 text-white rounded-xl'><Send size={20} /></button>
                        </div>
                    </>
                ) : <div className='flex-1 flex items-center justify-center text-gray-400'>یک تیکت انتخاب کنید</div>}
            </div>
        </div>
    );
};

export default TicketsTab;""",

    "frontend/src/components/admin/AnnouncementsTab.tsx": """import React, { useState, useRef } from 'react';
import { Megaphone, Image as ImageIcon, Send, Trash2 } from 'lucide-react';
import { Announcement } from '../../types';

interface AnnouncementsTabProps {
    announcements: Announcement[];
    onSendAnnouncement: (title: string, message: string, file?: File) => Promise<void>;
    onDeleteAnnouncement: (id: string) => void;
    isUploading: boolean;
}

const AnnouncementsTab: React.FC<AnnouncementsTabProps> = ({ announcements, onSendAnnouncement, onDeleteAnnouncement, isUploading }) => {
    const [title, setTitle] = useState('');
    const [message, setMessage] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSend = async () => {
        if (!title.trim() || !message.trim()) return;
        await onSendAnnouncement(title, message, file || undefined);
        setTitle(''); setMessage(''); setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
            <div className='lg:col-span-1 bg-white p-6 rounded-2xl shadow-sm border h-fit'>
                <h3 className='font-bold text-lg mb-4 flex items-center gap-2'><Megaphone size={20} className='text-orange-500' /> ارسال اطلاعیه</h3>
                <div className='space-y-4'>
                    <input value={title} onChange={(e) => setTitle(e.target.value)} className='w-full border rounded-xl px-4 py-2' placeholder='عنوان' />
                    <textarea value={message} onChange={(e) => setMessage(e.target.value)} className='w-full border rounded-xl px-4 py-2 h-32' placeholder='متن پیام...' />
                    <div className='flex items-center gap-2'>
                        <button onClick={() => fileInputRef.current?.click()} className='flex-1 border border-dashed border-gray-300 rounded-xl p-3 text-gray-500 flex items-center justify-center gap-2'><ImageIcon size={18} /> {file ? file.name : 'تصویر'}</button>
                        <input type='file' ref={fileInputRef} className='hidden' accept='image/*' onChange={(e) => setFile(e.target.files?.[0] || null)} />
                    </div>
                    <button onClick={handleSend} disabled={isUploading || !title || !message} className='w-full bg-blue-600 text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2'>{isUploading ? '...' : <><Send size={18} /> ارسال</>}</button>
                </div>
            </div>
            <div className='lg:col-span-2 space-y-4'>
                {announcements.map(ann => (
                    <div key={ann.id} className='bg-white p-4 rounded-2xl shadow-sm border flex gap-4'>
                        {ann.media_url && <img src={ann.media_url} alt='' className='w-24 h-24 object-cover rounded-xl bg-gray-100' />}
                        <div className='flex-1'>
                            <div className='flex justify-between'><h4 className='font-bold'>{ann.title}</h4><button onClick={() => onDeleteAnnouncement(ann.id.toString())} className='text-red-500'><Trash2 size={16} /></button></div>
                            <p className='text-gray-600 text-sm mt-1'>{ann.content || ann.message}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default AnnouncementsTab;""",

    "frontend/src/components/candidate/ProfileTab.tsx": """import React from 'react';
import { CandidateData } from '../../types';
import { User, Bot, Save } from 'lucide-react';

interface ProfileTabProps {
    formData: CandidateData;
    handleChange: (field: keyof CandidateData, value: string) => void;
    onSave: () => void;
}

const ProfileTab: React.FC<ProfileTabProps> = ({ formData, handleChange, onSave }) => {
    return (
        <div className='space-y-6'>
            <div className='bg-white p-6 rounded-2xl shadow-sm border'>
                <h3 className='text-lg font-bold mb-4 flex items-center gap-2'><User size={20} className='text-blue-600' /> اطلاعات پایه</h3>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>نام</label><input value={formData.name} onChange={(e) => handleChange('name', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>نام کاربری</label><input value={formData.username} disabled className='border rounded-xl px-4 py-2 bg-gray-100' /></div>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>شعار</label><input value={formData.slogan || ''} onChange={(e) => handleChange('slogan', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                </div>
            </div>
            <div className='bg-white p-6 rounded-2xl shadow-sm border'>
                <h3 className='text-lg font-bold mb-4 flex items-center gap-2'><Bot size={20} className='text-blue-600' /> تنظیمات ربات</h3>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>توکن ربات</label><input type='password' value={formData.bot_token || ''} onChange={(e) => handleChange('bot_token', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>نام ربات</label><input value={formData.bot_name || ''} onChange={(e) => handleChange('bot_name', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                </div>
            </div>
            <div className='flex justify-end'><button onClick={onSave} className='flex items-center gap-2 bg-green-600 text-white px-8 py-3 rounded-xl hover:bg-green-700'><Save size={20} /> ذخیره تغییرات</button></div>
        </div>
    );
};

export default ProfileTab;""",

    "frontend/src/components/candidate/PlansTab.tsx": """import React from 'react';
import { Plan } from '../../types';
import { Check } from 'lucide-react';

interface PlansTabProps {
    plans: Plan[];
    onSelectPlan: (plan: Plan) => void;
}

const PlansTab: React.FC<PlansTabProps> = ({ plans, onSelectPlan }) => {
    return (
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
            {plans.map(plan => (
                <div key={plan.id} className='bg-white p-6 rounded-2xl shadow-sm border hover:shadow-md transition'>
                    <h3 className='text-xl font-bold text-center mb-2'>{plan.title}</h3>
                    <p className='text-center text-2xl font-bold text-blue-600 mb-4'>{Number(plan.price).toLocaleString('fa-IR')} تومان</p>
                    <div className='space-y-2 mb-6'>
                        {plan.features.map((f, i) => (
                            <div key={i} className='flex items-center gap-2 text-sm text-gray-600'><Check size={16} className='text-green-500' />{f}</div>
                        ))}
                    </div>
                    <button onClick={() => onSelectPlan(plan)} className='w-full py-2 bg-blue-600 text-white rounded-xl'>خرید اشتراک</button>
                </div>
            ))}
        </div>
    );
};

export default PlansTab;""",

    "frontend/src/components/candidate/TicketsTab.tsx": """import React, { useState, useRef } from 'react';
import { Ticket } from '../../types';
import { Plus, Send, Paperclip } from 'lucide-react';

interface TicketsTabProps {
    tickets: Ticket[];
    onCreateTicket: (subject: string, message: string) => Promise<void>;
    onReplyTicket: (ticketId: string, message: string, attachment?: File) => Promise<void>;
    isUploading: boolean;
}

const TicketsTab: React.FC<TicketsTabProps> = ({ tickets, onCreateTicket, onReplyTicket, isUploading }) => {
    const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
    const [isNewMode, setIsNewMode] = useState(false);
    const [subject, setSubject] = useState('');
    const [message, setMessage] = useState('');
    const [replyMsg, setReplyMsg] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const activeTicket = tickets.find(t => t.id === activeTicketId);

    const handleCreate = async () => {
        if (!subject || !message) return;
        await onCreateTicket(subject, message);
        setSubject(''); setMessage(''); setIsNewMode(false);
    };

    const handleReply = async () => {
        if (!activeTicketId || !replyMsg) return;
        await onReplyTicket(activeTicketId, replyMsg);
        setReplyMsg('');
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !activeTicketId) return;
        await onReplyTicket(activeTicketId, '', file);
        e.target.value = '';
    };

    return (
        <div className='flex h-[600px] bg-white rounded-2xl shadow-sm border overflow-hidden'>
            <div className='w-1/3 border-l bg-gray-50 flex flex-col'>
                <div className='p-4 border-b'><button onClick={() => { setIsNewMode(true); setActiveTicketId(null); }} className='w-full py-2 bg-blue-600 text-white rounded-xl flex items-center justify-center gap-2'><Plus size={18} /> تیکت جدید</button></div>
                <div className='flex-1 overflow-y-auto'>
                    {tickets.map(t => (
                        <div key={t.id} onClick={() => { setActiveTicketId(t.id); setIsNewMode(false); }} className={`p-4 border-b cursor-pointer hover:bg-gray-100 ${activeTicketId === t.id ? 'bg-blue-50' : ''}`}>
                            <h4 className='font-bold text-sm truncate'>{t.subject}</h4>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${t.status === 'OPEN' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-700'}`}>{t.status === 'OPEN' ? 'باز' : 'بسته'}</span>
                        </div>
                    ))}
                </div>
            </div>
            <div className='flex-1 flex flex-col'>
                {isNewMode ? (
                    <div className='p-6 flex flex-col gap-4'>
                        <h3 className='font-bold'>تیکت جدید</h3>
                        <input value={subject} onChange={e => setSubject(e.target.value)} className='border rounded-xl px-4 py-2' placeholder='موضوع' />
                        <textarea value={message} onChange={e => setMessage(e.target.value)} className='border rounded-xl px-4 py-2 h-40' placeholder='پیام...' />
                        <button onClick={handleCreate} className='bg-blue-600 text-white px-6 py-2 rounded-xl self-end'>ارسال</button>
                    </div>
                ) : activeTicket ? (
                    <>
                        <div className='flex-1 overflow-y-auto p-4 space-y-4'>
                            {activeTicket.messages.map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.senderRole === 'CANDIDATE' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[70%] p-3 rounded-2xl ${msg.senderRole === 'CANDIDATE' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
                                        <p>{msg.text}</p>
                                        {msg.attachmentUrl && <a href={msg.attachmentUrl} target='_blank' className='block mt-2 text-xs underline'>دانلود فایل</a>}
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className='p-4 border-t bg-gray-50 flex gap-2 items-center'>
                            <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className='p-2 text-gray-500'><Paperclip size={20} /></button>
                            <input type='file' ref={fileInputRef} className='hidden' onChange={handleFileUpload} />
                            <input className='flex-1 border rounded-xl px-4 py-2' value={replyMsg} onChange={e => setReplyMsg(e.target.value)} placeholder='پاسخ...' />
                            <button onClick={handleReply} disabled={isUploading} className='p-2 bg-blue-600 text-white rounded-xl'><Send size={20} /></button>
                        </div>
                    </>
                ) : <div className='flex-1 flex items-center justify-center text-gray-400'>یک تیکت انتخاب کنید</div>}
            </div>
        </div>
    );
};

export default TicketsTab;""",

    "frontend/src/components/candidate/AnnouncementsTab.tsx": """import React from 'react';
import { Announcement } from '../../types';
import { Megaphone } from 'lucide-react';

interface AnnouncementsTabProps {
    announcements: Announcement[];
}

const AnnouncementsTab: React.FC<AnnouncementsTabProps> = ({ announcements }) => {
    return (
        <div className='space-y-4'>
            {announcements.map(ann => (
                <div key={ann.id} className='bg-white p-6 rounded-2xl shadow-sm border'>
                    <div className='flex items-center gap-2 mb-2'>
                        <Megaphone size={20} className='text-orange-500' />
                        <h3 className='font-bold'>{ann.title}</h3>
                        <span className='text-xs text-gray-400 mr-auto'>{new Date(ann.created_at).toLocaleDateString('fa-IR')}</span>
                    </div>
                    <p className='text-gray-700 leading-relaxed'>{ann.content || ann.message}</p>
                    {ann.media_url && <img src={ann.media_url} alt='' className='mt-4 rounded-xl max-h-60 object-cover' />}
                </div>
            ))}
            {announcements.length === 0 && <p className='text-center text-gray-500'>اطلاعیه‌ای وجود ندارد.</p>}
        </div>
    );
};

export default AnnouncementsTab;""",

    "frontend/src/components/AdminPanel.tsx": """import React, { useState, useEffect } from 'react';
import { api } from '@/services/api';
import { CandidateData, Plan, Ticket, Announcement } from '../types';
import { Users, CreditCard, MessageSquare, Megaphone, LogOut, LayoutDashboard, Menu } from 'lucide-react';
import CandidatesTab from './admin/CandidatesTab';
import PlansTab from './admin/PlansTab';
import TicketsTab from './admin/TicketsTab';
import AnnouncementsTab from './admin/AnnouncementsTab';

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

export default AdminPanel;""",

    "frontend/src/components/CandidatePanel.tsx": """import React, { useState, useEffect } from 'react';
import { api } from '@/services/api';
import { CandidateData, Plan, Ticket, Announcement } from '../types';
import { FileText, CreditCard, MessageSquare, Bell, LogOut, User, Menu, X } from 'lucide-react';
import ProfileTab from './candidate/ProfileTab';
import PlansTab from './candidate/PlansTab';
import TicketsTab from './candidate/TicketsTab';
import AnnouncementsTab from './candidate/AnnouncementsTab';

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

export default CandidatePanel;"""
}

for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {path}")
