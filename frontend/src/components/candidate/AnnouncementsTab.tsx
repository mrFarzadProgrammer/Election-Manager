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

                    {ann.attachments && ann.attachments.length > 0 && (
                        <div className='mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4'>
                            {ann.attachments.map((att, idx) => (
                                <div key={idx} className="bg-gray-50 p-2 rounded-xl border border-gray-200 shadow-sm">
                                    {att.type === 'IMAGE' && (
                                        <img src={att.url} alt={`attachment-${idx}`} className='w-full h-64 object-cover rounded-lg' />
                                    )}
                                    {att.type === 'VIDEO' && (
                                        <video src={att.url} controls className='w-full h-64 object-cover rounded-lg bg-black' />
                                    )}
                                    {att.type === 'VOICE' && (
                                        <div className="flex items-center justify-center h-24 bg-white rounded-lg">
                                            <audio src={att.url} controls className='w-full px-2' />
                                        </div>
                                    )}
                                    {(!att.type || att.type === 'FILE') && (
                                        <a href={att.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-blue-600 bg-blue-50 p-4 rounded-lg hover:bg-blue-100 transition h-full justify-center font-medium">
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
                <div className='flex flex-col items-center justify-center py-12 text-gray-400'>
                    <Megaphone size={48} className='mb-4 opacity-20' />
                    <p>هنوز هیچ اطلاعیه‌ای ارسال نشده است</p>
                </div>
            )}
        </div>
    );
};

export default AnnouncementsTab;