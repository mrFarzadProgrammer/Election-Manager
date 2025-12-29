import React from 'react';
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

export default AnnouncementsTab;