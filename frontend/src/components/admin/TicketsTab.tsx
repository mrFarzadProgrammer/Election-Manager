import React, { useState, useRef, useEffect } from 'react';
import { Ticket } from '../../types';
import { Send, Paperclip, Search, MoreVertical, Image as ImageIcon, Mic, FileText, ArrowRight, MessageSquare } from 'lucide-react';
import { toJalaali } from 'jalaali-js';

interface TicketsTabProps {
    tickets: Ticket[];
    onReply: (ticketId: string, message: string, attachment?: File) => Promise<void>;
    onCloseTicket: (ticketId: string) => void;
    isUploading: boolean;
}

const TicketsTab: React.FC<TicketsTabProps> = ({ tickets, onReply, onCloseTicket, isUploading }) => {
    const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
    const [replyMsg, setReplyMsg] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const activeTicket = tickets.find(t => t.id === activeTicketId);

    // Filter and sort tickets
    const filteredTickets = tickets
        .filter(t =>
            t.subject.includes(searchQuery) ||
            (t.userName || '').includes(searchQuery)
        )
        .sort((a, b) => b.lastUpdate - a.lastUpdate);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [activeTicket?.messages]);

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

    const formatTime = (timestamp: number) => {
        if (!timestamp || isNaN(timestamp)) return '';
        try {
            const date = new Date(timestamp);
            const jDate = toJalaali(date);
            const time = date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
            return `${jDate.jy}/${jDate.jm}/${jDate.jd} ${time}`;
        } catch (e) {
            return '';
        }
    };

    const getFullUrl = (url?: string) => {
        if (!url) return undefined;
        if (url.startsWith('http')) return url;
        const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
        return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
    };

    return (
        <div className='flex h-[calc(100vh-140px)] bg-white rounded-3xl shadow-sm border overflow-hidden'>
            {/* Right Sidebar - Ticket List */}
            <div className={`w-full md:w-80 border-l bg-white flex flex-col ${activeTicketId ? 'hidden md:flex' : 'flex'}`}>
                <div className='p-4 border-b'>
                    <div className='flex justify-between items-center mb-4'>
                        <h3 className='font-bold text-lg text-gray-800'>صندوق پیام‌ها</h3>
                        <span className='bg-blue-100 text-blue-600 text-xs px-2 py-1 rounded-full font-bold'>
                            {tickets.filter(t => t.status === 'OPEN').length} پیام جدید
                        </span>
                    </div>
                    <div className='relative'>
                        <Search size={18} className='absolute right-3 top-1/2 -translate-y-1/2 text-gray-400' />
                        <input
                            type="text"
                            placeholder="جستجو..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className='w-full bg-gray-100 rounded-xl pr-10 pl-4 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-100 transition'
                        />
                    </div>
                </div>

                <div className='flex-1 overflow-y-auto'>
                    {filteredTickets.map(ticket => (
                        <div
                            key={ticket.id}
                            onClick={() => setActiveTicketId(ticket.id)}
                            className={`p-4 border-b cursor-pointer hover:bg-gray-50 transition relative group ${activeTicketId === ticket.id ? 'bg-blue-50/50' : ''}`}
                        >
                            <div className='flex justify-between items-start mb-1'>
                                <h4 className='font-bold text-gray-800 truncate max-w-[140px]'>{ticket.userName || 'کاربر ناشناس'}</h4>
                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${ticket.status === 'OPEN' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'}`}>
                                    {ticket.status === 'OPEN' ? 'باز' : 'بسته'}
                                </span>
                            </div>
                            <p className='text-sm text-gray-600 font-medium mb-1 truncate'>{ticket.subject}</p>
                            <p className='text-xs text-gray-400 truncate'>
                                {(ticket.messages && ticket.messages.length > 0)
                                    ? (ticket.messages[ticket.messages.length - 1]?.text || 'بدون متن')
                                    : 'بدون پیام'}
                            </p>
                            {activeTicketId === ticket.id && (
                                <div className='absolute left-0 top-0 bottom-0 w-1 bg-blue-600 rounded-r-full'></div>
                            )}
                        </div>
                    ))}
                    {filteredTickets.length === 0 && (
                        <div className='p-8 text-center text-gray-400 text-sm'>
                            پیامی یافت نشد
                        </div>
                    )}
                </div>
            </div>

            {/* Left Main Area - Chat Interface */}
            <div className={`flex-1 flex flex-col bg-gray-50/30 ${!activeTicketId ? 'hidden md:flex' : 'flex'}`}>
                {activeTicket ? (
                    <>
                        {/* Chat Header */}
                        <div className='p-4 border-b bg-white flex justify-between items-center shadow-sm z-10'>
                            <div className='flex items-center gap-3'>
                                <button onClick={() => setActiveTicketId(null)} className='md:hidden p-2 hover:bg-gray-100 rounded-full'>
                                    <ArrowRight size={20} className='text-gray-600' />
                                </button>
                                <div className='w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold'>
                                    {(activeTicket.userName || '?')[0]}
                                </div>
                                <div>
                                    <h3 className='font-bold text-gray-800'>{activeTicket.userName}</h3>
                                    <p className='text-xs text-gray-500'>{activeTicket.subject}</p>
                                </div>
                            </div>
                            <div className='flex items-center gap-2'>
                                <button className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition'>
                                    <MoreVertical size={20} />
                                </button>
                            </div>
                        </div>

                        {/* Messages Area */}
                        <div className='flex-1 overflow-y-auto p-4 space-y-6 bg-[#f8f9fa]'>
                            {(activeTicket.messages || []).map((msg, idx) => {
                                const isAdmin = (msg.senderRole || '').toUpperCase() === 'ADMIN';
                                const fileUrl = getFullUrl(msg.attachmentUrl);

                                return (
                                    <div key={idx} className={`flex ${isAdmin ? 'justify-end' : 'justify-start'}`} dir="ltr">
                                        <div className={`max-w-[75%] md:max-w-[60%] flex flex-col ${isAdmin ? 'items-end' : 'items-start'}`}>
                                            <div
                                                className={`p-3 rounded-2xl shadow-sm relative group text-right ${isAdmin
                                                    ? 'bg-blue-600 text-white rounded-br-none'
                                                    : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                                                    }`}
                                                dir="rtl"
                                            >
                                                {msg.text && (
                                                    <div className="mb-1">
                                                        <p className='text-sm leading-relaxed whitespace-pre-wrap break-words'>{msg.text}</p>
                                                    </div>
                                                )}

                                                {fileUrl && (
                                                    <div className={`mt-2 rounded-xl overflow-hidden ${isAdmin ? 'bg-white/10' : 'bg-gray-50 border'}`}>
                                                        {msg.attachmentType === 'IMAGE' ? (
                                                            <a href={fileUrl} target='_blank' rel="noreferrer" className="block">
                                                                <img src={fileUrl} alt="attachment" className="max-w-full h-auto max-h-60 object-cover" />
                                                            </a>
                                                        ) : (
                                                            <a
                                                                href={fileUrl}
                                                                target='_blank'
                                                                rel="noreferrer"
                                                                className={`flex items-center gap-3 p-3 text-sm ${isAdmin ? 'text-white hover:bg-white/20' : 'text-blue-600 hover:bg-gray-100'} transition`}
                                                            >
                                                                <div className={`p-2 rounded-lg ${isAdmin ? 'bg-white/20' : 'bg-blue-50'}`}>
                                                                    <FileText size={20} />
                                                                </div>
                                                                <div className='flex flex-col'>
                                                                    <span className='font-medium'>دانلود فایل پیوست</span>
                                                                    <span className={`text-xs ${isAdmin ? 'text-white/70' : 'text-gray-400'}`}>برای مشاهده کلیک کنید</span>
                                                                </div>
                                                            </a>
                                                        )}
                                                    </div>
                                                )}

                                                <div className={`flex items-center justify-end gap-1 mt-1 ${isAdmin ? 'text-blue-100' : 'text-gray-400'}`}>
                                                    <span className="text-[10px]">{formatTime(msg.timestamp)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className='p-4 bg-white border-t'>
                            <div className='flex items-end gap-2 bg-gray-50 p-2 rounded-2xl border focus-within:border-blue-300 focus-within:ring-4 focus-within:ring-blue-50 transition'>
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={isUploading}
                                    className='p-3 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition'
                                    title="ارسال فایل"
                                >
                                    <Paperclip size={20} />
                                </button>
                                <input
                                    type='file'
                                    ref={fileInputRef}
                                    className='hidden'
                                    onChange={handleFileUpload}
                                />

                                <textarea
                                    className='flex-1 bg-transparent border-none outline-none text-sm py-3 px-2 resize-none max-h-32 min-h-[44px]'
                                    placeholder='پیام خود را بنویسید...'
                                    value={replyMsg}
                                    onChange={(e) => setReplyMsg(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleSend();
                                        }
                                    }}
                                    disabled={isUploading}
                                    rows={1}
                                    style={{ height: 'auto' }}
                                    onInput={(e) => {
                                        const target = e.target as HTMLTextAreaElement;
                                        target.style.height = 'auto';
                                        target.style.height = `${Math.min(target.scrollHeight, 128)}px`;
                                    }}
                                />

                                {replyMsg.trim() || isUploading ? (
                                    <button
                                        onClick={handleSend}
                                        disabled={isUploading}
                                        className={`p-3 rounded-xl transition ${isUploading ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-600/30'}`}
                                    >
                                        <Send size={20} className={isUploading ? 'animate-pulse' : ''} />
                                    </button>
                                ) : (
                                    <button className='p-3 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-xl transition'>
                                        <Mic size={20} />
                                    </button>
                                )}
                            </div>
                            <div className='text-center mt-2'>
                                <p className='text-[10px] text-gray-400'>
                                    Enter برای ارسال، Shift + Enter برای خط جدید
                                </p>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className='flex-1 flex flex-col items-center justify-center text-gray-400 bg-gray-50/50'>
                        <div className='w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4'>
                            <MessageSquare size={40} className='text-gray-300' />
                        </div>
                        <h3 className='text-lg font-bold text-gray-600 mb-2'>خوش آمدید</h3>
                        <p className='text-sm text-gray-500'>برای شروع گفتگو، یک پیام را از لیست انتخاب کنید</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TicketsTab;