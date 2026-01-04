import React, { useState, useRef } from 'react';
import { Megaphone, Image as ImageIcon, Send, Trash2, Video, Mic, FileText, X } from 'lucide-react';
import { Announcement } from '../../types';

interface AnnouncementsTabProps {
    announcements: Announcement[];
    onSendAnnouncement: (title: string, message: string, files: File[]) => Promise<void>;
    onDeleteAnnouncement: (id: string) => void;
    isUploading: boolean;
}

const AnnouncementsTab: React.FC<AnnouncementsTabProps> = ({ announcements, onSendAnnouncement, onDeleteAnnouncement, isUploading }) => {
    const [title, setTitle] = useState('');
    const [message, setMessage] = useState('');
    const [files, setFiles] = useState<File[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSend = async () => {
        if (!title.trim() || !message.trim()) return;
        await onSendAnnouncement(title, message, files);
        setTitle(''); setMessage(''); setFiles([]);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
        }
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
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
                            className={`border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center cursor-pointer transition ${files.length > 0 ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'}`}
                        >
                            <div className='flex gap-3 text-gray-400 mb-2'>
                                <ImageIcon size={24} />
                                <Video size={24} />
                                <Mic size={24} />
                            </div>
                            <p className='text-sm text-gray-500'>برای انتخاب فایل‌ها کلیک کنید</p>
                            <p className='text-xs text-gray-400 mt-1'>حداکثر حجم: ۵۰ مگابایت</p>
                        </div>
                        <input
                            type='file'
                            ref={fileInputRef}
                            className='hidden'
                            multiple
                            accept='image/*,video/*,audio/*'
                            onChange={handleFileChange}
                        />
                    </div>

                    {/* Selected Files List */}
                    {files.length > 0 && (
                        <div className="space-y-2 max-h-40 overflow-y-auto">
                            {files.map((file, index) => (
                                <div key={index} className='flex items-center gap-3 w-full bg-gray-50 p-2 rounded-lg border border-gray-200'>
                                    <div className='p-2 bg-white rounded-lg shadow-sm text-blue-600'>
                                        {getFileIcon(file.type)}
                                    </div>
                                    <div className='flex-1 min-w-0'>
                                        <p className='text-sm font-medium text-gray-800 truncate'>{file.name}</p>
                                        <p className='text-xs text-gray-500'>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                    </div>
                                    <button
                                        onClick={() => removeFile(index)}
                                        className='p-1 hover:bg-red-100 text-red-500 rounded-full transition'
                                    >
                                        <X size={18} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

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

                            {ann.attachments && ann.attachments.length > 0 && (
                                <div className='mr-12 grid grid-cols-1 sm:grid-cols-2 gap-4'>
                                    {ann.attachments.map((att, idx) => (
                                        <div key={idx} className="bg-white p-2 rounded-xl border border-gray-200 shadow-sm">
                                            {att.type === 'IMAGE' && (
                                                <img src={att.url} alt={`attachment-${idx}`} className='w-full h-48 object-cover rounded-lg' />
                                            )}
                                            {att.type === 'VIDEO' && (
                                                <video src={att.url} controls className='w-full h-48 object-cover rounded-lg bg-black' />
                                            )}
                                            {att.type === 'VOICE' && (
                                                <div className="flex items-center justify-center h-20 bg-gray-100 rounded-lg">
                                                    <audio src={att.url} controls className='w-full px-2' />
                                                </div>
                                            )}
                                            {(!att.type || att.type === 'FILE') && (
                                                <a href={att.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-blue-600 bg-blue-50 p-4 rounded-lg hover:bg-blue-100 transition h-full justify-center">
                                                    <FileText size={24} />
                                                    <span>دانلود فایل</span>
                                                </a>
                                            )}
                                        </div>
                                    ))}
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