import React, { useState, useRef } from 'react';
import { Megaphone, Image as ImageIcon, Send, Trash2, Video, Mic, FileText, X } from 'lucide-react';
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

    const getFileIcon = (type: string) => {
        if (type.startsWith('image/')) return <ImageIcon size={20} />;
        if (type.startsWith('video/')) return <Video size={20} />;
        if (type.startsWith('audio/')) return <Mic size={20} />;
        return <FileText size={20} />;
    };

    return (
        <div className='grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]'>
            {/* Left Side - Form */}
            <div className='lg:col-span-1 bg-white p-6 rounded-3xl shadow-sm border h-fit'>
                <div className='flex items-center justify-between mb-6'>
                    <h3 className='font-bold text-lg text-gray-800 flex items-center gap-2'>
                        <Megaphone size={24} className='text-orange-500' />
                        ارسال اطلاعیه
                    </h3>
                </div>

                <div className='space-y-4'>
                    <div>
                        <label className='block text-sm font-medium text-gray-700 mb-1'>عنوان</label>
                        <input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className='w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition'
                            placeholder='عنوان اطلاعیه را وارد کنید...'
                        />
                    </div>

                    <div>
                        <label className='block text-sm font-medium text-gray-700 mb-1'>متن پیام</label>
                        <textarea
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            className='w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 h-40 resize-none outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition'
                            placeholder='متن پیام خود را بنویسید...'
                        />
                    </div>

                    <div>
                        <label className='block text-sm font-medium text-gray-700 mb-1'>پیوست فایل (تصویر، ویدیو، صدا)</label>
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className={`border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center cursor-pointer transition ${file ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'}`}
                        >
                            {file ? (
                                <div className='flex items-center gap-3 w-full'>
                                    <div className='p-2 bg-white rounded-lg shadow-sm text-blue-600'>
                                        {getFileIcon(file.type)}
                                    </div>
                                    <div className='flex-1 min-w-0'>
                                        <p className='text-sm font-medium text-gray-800 truncate'>{file.name}</p>
                                        <p className='text-xs text-gray-500'>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                                        className='p-1 hover:bg-red-100 text-red-500 rounded-full transition'
                                    >
                                        <X size={18} />
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className='flex gap-3 text-gray-400 mb-2'>
                                        <ImageIcon size={24} />
                                        <Video size={24} />
                                        <Mic size={24} />
                                    </div>
                                    <p className='text-sm text-gray-500'>برای انتخاب فایل کلیک کنید</p>
                                    <p className='text-xs text-gray-400 mt-1'>حداکثر حجم: ۵۰ مگابایت</p>
                                </>
                            )}
                        </div>
                        <input
                            type='file'
                            ref={fileInputRef}
                            className='hidden'
                            accept='image/*,video/*,audio/*'
                            onChange={(e) => setFile(e.target.files?.[0] || null)}
                        />
                    </div>

                    <button
                        onClick={handleSend}
                        disabled={isUploading || !title || !message}
                        className={`w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition shadow-lg shadow-blue-600/20 ${isUploading || !title || !message ? 'bg-gray-300 text-gray-500 cursor-not-allowed shadow-none' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
                    >
                        {isUploading ? (
                            <span className='animate-pulse'>در حال ارسال...</span>
                        ) : (
                            <>
                                <Send size={20} />
                                ارسال اطلاعیه
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Right Side - List */}
            <div className='lg:col-span-2 flex flex-col h-full overflow-hidden bg-white rounded-3xl shadow-sm border'>
                <div className='p-6 border-b flex justify-between items-center'>
                    <h3 className='font-bold text-lg text-gray-800'>تاریخچه اطلاعیه‌ها</h3>
                    <span className='bg-blue-100 text-blue-600 text-xs px-3 py-1 rounded-full font-bold'>
                        {announcements.length} مورد
                    </span>
                </div>

                <div className='flex-1 overflow-y-auto p-6 space-y-4'>
                    {announcements.map(ann => (
                        <div key={ann.id} className='bg-gray-50 p-4 rounded-2xl border border-gray-100 hover:border-blue-200 transition group'>
                            <div className='flex justify-between items-start mb-3'>
                                <div className='flex items-center gap-3'>
                                    <div className='w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-sm text-orange-500'>
                                        <Megaphone size={20} />
                                    </div>
                                    <div>
                                        <h4 className='font-bold text-gray-800'>{ann.title}</h4>
                                        <span className='text-xs text-gray-400'>
                                            {new Date(ann.created_at).toLocaleDateString('fa-IR')}
                                        </span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => onDeleteAnnouncement(ann.id)}
                                    className='p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition opacity-0 group-hover:opacity-100'
                                    title="حذف"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>

                            <p className='text-gray-600 text-sm leading-relaxed mb-4 whitespace-pre-wrap pl-12'>
                                {ann.content}
                            </p>

                            {ann.media_url && (
                                <div className='mr-12'>
                                    {ann.media_type === 'IMAGE' && (
                                        <img src={ann.media_url} alt={ann.title} className='max-h-60 rounded-xl object-cover shadow-sm' />
                                    )}
                                    {ann.media_type === 'VIDEO' && (
                                        <video src={ann.media_url} controls className='max-h-60 rounded-xl shadow-sm w-full max-w-md bg-black' />
                                    )}
                                    {ann.media_type === 'VOICE' && (
                                        <audio src={ann.media_url} controls className='w-full max-w-md' />
                                    )}
                                    {(!ann.media_type || ann.media_type === 'FILE') && (
                                        <a href={ann.media_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-blue-600 bg-blue-50 px-4 py-2 rounded-xl hover:bg-blue-100 transition">
                                            <FileText size={18} />
                                            دانلود فایل پیوست
                                        </a>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}

                    {announcements.length === 0 && (
                        <div className='flex flex-col items-center justify-center h-full text-gray-400'>
                            <Megaphone size={48} className='mb-4 opacity-20' />
                            <p>هنوز هیچ اطلاعیه‌ای ارسال نشده است</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AnnouncementsTab;