import React, { useState, useRef, useEffect } from 'react';
import { Ticket } from '../../types';
import { Plus, Send, Paperclip, Search, ArrowRight, MoreVertical, FileText, Image as ImageIcon, X, ChevronLeft } from 'lucide-react';
import { toJalaali } from 'jalaali-js';

interface SupportChatProps {
    tickets: Ticket[];
    onCreateTicket: (subject: string, message: string) => Promise<void>;
    onReplyTicket: (ticketId: string, message: string, attachment?: File) => Promise<void>;
    onTicketOpen?: (ticketId: string) => void;
    isUploading: boolean;
    readTicketTimes?: { [key: string]: number };
}

const SupportChat: React.FC<SupportChatProps> = ({ tickets, onCreateTicket, onReplyTicket, isUploading, onTicketOpen, readTicketTimes = {} }) => {
    const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
    const [isNewMode, setIsNewMode] = useState(false);
    const [subject, setSubject] = useState('');
    const [message, setMessage] = useState('');
    const [replyMsg, setReplyMsg] = useState('');
    const [searchTerm, setSearchTerm] = useState('');
    const [showMobileList, setShowMobileList] = useState(true);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const activeTicket = tickets.find(t => t.id === activeTicketId);

    // Filter tickets based on search
    const filteredTickets = tickets.filter(t =>
        t.subject.includes(searchTerm) ||
        t.id.includes(searchTerm)
    );

    useEffect(() => {
        if (activeTicketId || isNewMode) {
            setShowMobileList(false);
        } else {
            setShowMobileList(true);
        }
    }, [activeTicketId, isNewMode]);

    useEffect(() => {
        scrollToBottom();
    }, [activeTicket?.messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleCreate = async () => {
        if (!subject || !message) return;
        await onCreateTicket(subject, message);
        setSubject('');
        setMessage('');
        setIsNewMode(false);
        // Optionally select the newly created ticket if we could get its ID
        setShowMobileList(true); // Go back to list on mobile or stay in view
    };

    const handleReply = async () => {
        if (!activeTicketId || !replyMsg.trim()) return;
        await onReplyTicket(activeTicketId, replyMsg);
        setReplyMsg('');
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !activeTicketId) return;
        await onReplyTicket(activeTicketId, '', file);
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
        <div className="flex h-[calc(100vh-140px)] bg-gray-50 gap-4 p-4 md:p-0 overflow-hidden">
            {/* Sidebar (Right Side) */}
            <div className={`w-full md:w-80 lg:w-96 bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden transition-all duration-300 ${showMobileList ? 'flex' : 'hidden md:flex'}`}>
                {/* Sidebar Header */}
                <div className="p-5 border-b flex items-center justify-between bg-white">
                    <h2 className="font-bold text-gray-800">تیکت‌های من</h2>
                    <button
                        onClick={() => { setIsNewMode(true); setActiveTicketId(null); }}
                        className="w-8 h-8 flex items-center justify-center bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 transition-colors"
                    >
                        <Plus size={20} />
                    </button>
                </div>

                {/* Search */}
                <div className="p-4 pb-2">
                    <div className="relative">
                        <Search size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            placeholder="جستجو در تیکت‌ها..."
                            className="w-full bg-gray-50 border border-gray-100 rounded-xl pr-10 pl-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-100 focus:border-blue-200 outline-none transition-all"
                        />
                    </div>
                </div>

                {/* Ticket List */}
                <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
                    {filteredTickets.length > 0 ? (
                        filteredTickets.map(t => {
                            const lastRead = readTicketTimes[t.id] || 0;
                            const isUnread = t.status === 'ANSWERED' && t.lastUpdate > lastRead;

                            return (
                                <div
                                    key={t.id}
                                    onClick={() => {
                                        setActiveTicketId(t.id);
                                        setIsNewMode(false);
                                        onTicketOpen?.(t.id);
                                    }}
                                    className={`p-4 rounded-2xl cursor-pointer transition-all border ${activeTicketId === t.id
                                        ? 'bg-blue-50 border-blue-100 shadow-sm'
                                        : 'bg-white border-transparent hover:bg-gray-50 hover:border-gray-100'
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className={`text-[10px] px-2 py-1 rounded-full font-medium ${isUnread
                                            ? 'bg-red-500 text-white animate-pulse shadow-sm'
                                            : t.status === 'ANSWERED'
                                                ? 'bg-green-100 text-green-700'
                                                : 'bg-gray-100 text-gray-600'
                                            }`}>
                                            {isUnread ? 'پیام جدید' : t.status === 'ANSWERED' ? 'پاسخ داده شده' : t.status === 'OPEN' ? 'باز' : 'بسته شده'}
                                        </span>
                                        <span className="text-[10px] text-gray-400">{formatTime(t.lastUpdate)}</span>
                                    </div>
                                    <h4 className={`font-bold text-sm mb-1 truncate ${activeTicketId === t.id ? 'text-blue-800' : 'text-gray-800'}`}>
                                        {t.subject}
                                    </h4>
                                    <p className="text-xs text-gray-500 truncate">
                                        {t.messages[t.messages.length - 1]?.text || 'بدون پیام'}
                                    </p>
                                </div>
                            );
                        })
                    ) : (
                        <div className="text-center py-10 text-gray-400">
                            <p className="text-sm">تیکتی یافت نشد</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Chat Area (Left Side) */}
            <div className={`flex-1 flex flex-col bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden transition-all duration-300 ${showMobileList ? 'hidden md:flex' : 'flex'}`}>
                {isNewMode ? (
                    // New Ticket Form
                    <div className="flex flex-col h-full">
                        <div className="p-4 border-b flex items-center gap-3 bg-white">
                            <button onClick={() => { setIsNewMode(false); setShowMobileList(true); }} className="md:hidden p-2 hover:bg-gray-100 rounded-full">
                                <ArrowRight size={20} />
                            </button>
                            <h3 className="font-bold text-gray-800">تیکت جدید</h3>
                        </div>
                        <div className="p-6 flex flex-col gap-4 flex-1 overflow-y-auto">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">موضوع تیکت</label>
                                <input
                                    value={subject}
                                    onChange={e => setSubject(e.target.value)}
                                    className="w-full border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                                    placeholder="مثلا: مشکل در آپلود مدارک"
                                />
                            </div>
                            <div className="flex-1 flex flex-col">
                                <label className="block text-sm font-medium text-gray-700 mb-2">پیام شما</label>
                                <textarea
                                    value={message}
                                    onChange={e => setMessage(e.target.value)}
                                    className="w-full flex-1 border border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none"
                                    placeholder="توضیحات کامل مشکل یا درخواست خود را بنویسید..."
                                />
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button
                                    onClick={() => { setIsNewMode(false); setShowMobileList(true); }}
                                    className="px-6 py-2.5 text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                                >
                                    انصراف
                                </button>
                                <button
                                    onClick={handleCreate}
                                    disabled={!subject || !message}
                                    className="px-6 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-200"
                                >
                                    ارسال تیکت
                                </button>
                            </div>
                        </div>
                    </div>
                ) : activeTicket ? (
                    // Active Chat View
                    <>
                        {/* Chat Header */}
                        <div className="px-6 py-4 border-b flex items-center justify-between bg-white z-10">
                            <div className="flex items-center gap-3">
                                <button onClick={() => { setActiveTicketId(null); setShowMobileList(true); }} className="md:hidden p-2 -mr-2 hover:bg-gray-100 rounded-full text-gray-500">
                                    <ArrowRight size={20} />
                                </button>
                                <div>
                                    <h3 className="font-bold text-gray-800">{activeTicket.subject}</h3>
                                    <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                                        <span>شناسه تیکت: #{activeTicket.id.substring(0, 6)}</span>
                                        <span className="w-1 h-1 rounded-full bg-gray-300"></span>
                                        <span className={`${activeTicket.status === 'ANSWERED' ? 'text-green-600' : 'text-gray-500'}`}>
                                            {activeTicket.status === 'ANSWERED' ? 'پاسخ داده شده' : activeTicket.status === 'OPEN' ? 'باز' : 'بسته شده'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <button className="p-2 text-gray-400 hover:bg-gray-50 rounded-xl transition-colors">
                                <MoreVertical size={20} />
                            </button>
                        </div>

                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/50">
                            {(activeTicket.messages || []).map((msg, idx) => {
                                const isMe = (msg.senderRole || '').toUpperCase() === 'CANDIDATE';
                                const fileUrl = getFullUrl(msg.attachmentUrl);

                                return (
                                    <div key={idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`} dir="ltr">
                                        <div className={`max-w-[85%] md:max-w-[70%] flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                                            <div
                                                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm relative group text-right ${isMe
                                                    ? 'bg-blue-600 text-white rounded-br-none'
                                                    : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                                                    }`}
                                                dir="rtl"
                                            >
                                                <div className="mb-1">
                                                    <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                                                </div>

                                                {fileUrl && (
                                                    <div className="my-2">
                                                        {msg.attachmentType === 'IMAGE' ? (
                                                            <a href={fileUrl} target="_blank" rel="noreferrer" className="block">
                                                                <img src={fileUrl} alt="attachment" className="max-w-full h-auto max-h-48 object-cover rounded-lg" />
                                                            </a>
                                                        ) : (
                                                            <a
                                                                href={fileUrl}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className={`flex items-center gap-2 p-2 rounded-lg ${isMe ? 'bg-blue-700/50 hover:bg-blue-700' : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'} transition-colors`}
                                                            >
                                                                <div className={`p-1.5 rounded-md ${isMe ? 'bg-white/20' : 'bg-white shadow-sm'}`}>
                                                                    <Paperclip size={16} />
                                                                </div>
                                                                <span className="text-xs opacity-90 truncate max-w-[150px]">دانلود فایل پیوست</span>
                                                            </a>
                                                        )}
                                                    </div>
                                                )}

                                                <div className={`flex items-center justify-end gap-1 mt-1 ${isMe ? 'text-blue-100' : 'text-gray-400'}`}>
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
                        <div className="p-4 bg-white border-t">
                            <div className="flex items-end gap-2 bg-gray-50 border border-gray-200 rounded-2xl p-2 focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-50 transition-all">
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={isUploading}
                                    className="p-3 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors"
                                >
                                    <Paperclip size={20} />
                                </button>
                                <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />

                                <textarea
                                    value={replyMsg}
                                    onChange={e => setReplyMsg(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleReply();
                                        }
                                    }}
                                    placeholder="پیام خود را بنویسید..."
                                    className="flex-1 bg-transparent border-none focus:ring-0 py-3 max-h-32 min-h-[44px] resize-none text-sm"
                                    rows={1}
                                />

                                <button
                                    onClick={handleReply}
                                    disabled={!replyMsg.trim() || isUploading}
                                    className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-blue-200 transition-all"
                                >
                                    {isUploading ? (
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    ) : (
                                        <Send size={20} className={document.dir === 'rtl' ? 'rotate-180' : ''} />
                                    )}
                                </button>
                            </div>
                        </div>
                    </>
                ) : (
                    // Empty State
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-400 bg-gray-50/50">
                        <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center shadow-sm mb-4">
                            <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center text-blue-500">
                                <FileText size={32} />
                            </div>
                        </div>
                        <h3 className="text-lg font-bold text-gray-700 mb-2">تیکتی انتخاب نشده</h3>
                        <p className="text-sm text-gray-500">برای مشاهده جزئیات، یک تیکت را از لیست انتخاب کنید</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SupportChat;
