import React, { useState, useRef } from 'react';
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

export default AnnouncementsTab;