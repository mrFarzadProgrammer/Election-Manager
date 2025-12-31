import React from 'react';
import { Announcement } from '../../types';
import { Megaphone, FileText } from 'lucide-react';

interface AnnouncementsTabProps {
    announcements: Announcement[];
}

const AnnouncementsTab: React.FC<AnnouncementsTabProps> = ({ announcements }) => {
    return (
        <div className='space-y-4'>
            {announcements.map(ann => (
                <div key={ann.id} className='bg-white p-6 rounded-2xl shadow-sm border'>
                    <div className='flex items-center gap-2 mb-4'>
                        <div className='w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center text-orange-600'>
                            <Megaphone size={20} />
                        </div>
                        <div>
                            <h3 className='font-bold text-gray-800'>{ann.title}</h3>
                            <span className='text-xs text-gray-400'>{new Date(ann.created_at).toLocaleDateString('fa-IR')}</span>
                        </div>
                    </div>

                    <p className='text-gray-700 leading-relaxed mb-4 whitespace-pre-wrap'>
                        {ann.content}
                    </p>

                    {ann.media_url && (
                        <div className='mt-4'>
                            {ann.media_type === 'IMAGE' && (
                                <img src={ann.media_url} alt={ann.title} className='max-h-80 rounded-xl object-cover shadow-sm w-full md:w-auto' />
                            )}
                            {ann.media_type === 'VIDEO' && (
                                <video src={ann.media_url} controls className='max-h-80 rounded-xl shadow-sm w-full max-w-lg bg-black' />
                            )}
                            {ann.media_type === 'VOICE' && (
                                <audio src={ann.media_url} controls className='w-full max-w-md' />
                            )}
                            {(!ann.media_type || ann.media_type === 'FILE') && (
                                <a href={ann.media_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-blue-600 bg-blue-50 px-4 py-3 rounded-xl hover:bg-blue-100 transition font-medium">
                                    <FileText size={20} />
                                    دانلود فایل پیوست
                                </a>
                            )}
                        </div>
                    )}
                </div>
            ))}
            {announcements.length === 0 && (
                <div className='flex flex-col items-center justify-center py-12 text-gray-400'>
                    <Megaphone size={48} className='mb-4 opacity-20' />
                    <p>هنوز هیچ اطلاعیه‌ای ارسال نشده است</p>
                </div>
            )}
        </div>
    );
};

export default AnnouncementsTab;