import React, { useState, useRef } from 'react';
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

export default TicketsTab;