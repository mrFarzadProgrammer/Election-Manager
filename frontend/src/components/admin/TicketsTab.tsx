import React, { useState, useRef } from 'react';
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

export default TicketsTab;