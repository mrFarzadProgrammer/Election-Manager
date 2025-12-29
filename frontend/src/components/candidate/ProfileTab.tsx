import React from 'react';
import { CandidateData } from '../../types';
import { User, Bot, Save } from 'lucide-react';

interface ProfileTabProps {
    formData: CandidateData;
    handleChange: (field: keyof CandidateData, value: string) => void;
    onSave: () => void;
}

const ProfileTab: React.FC<ProfileTabProps> = ({ formData, handleChange, onSave }) => {
    return (
        <div className='space-y-6'>
            <div className='bg-white p-6 rounded-2xl shadow-sm border'>
                <h3 className='text-lg font-bold mb-4 flex items-center gap-2'><User size={20} className='text-blue-600' /> اطلاعات پایه</h3>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>نام</label><input value={formData.name} onChange={(e) => handleChange('name', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>نام کاربری</label><input value={formData.username} disabled className='border rounded-xl px-4 py-2 bg-gray-100' /></div>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>شعار</label><input value={formData.slogan || ''} onChange={(e) => handleChange('slogan', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                </div>
            </div>
            <div className='bg-white p-6 rounded-2xl shadow-sm border'>
                <h3 className='text-lg font-bold mb-4 flex items-center gap-2'><Bot size={20} className='text-blue-600' /> تنظیمات ربات</h3>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>توکن ربات</label><input type='password' value={formData.bot_token || ''} onChange={(e) => handleChange('bot_token', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                    <div className='flex flex-col gap-2'><label className='text-sm font-medium'>نام ربات</label><input value={formData.bot_name || ''} onChange={(e) => handleChange('bot_name', e.target.value)} className='border rounded-xl px-4 py-2' /></div>
                </div>
            </div>
            <div className='flex justify-end'><button onClick={onSave} className='flex items-center gap-2 bg-green-600 text-white px-8 py-3 rounded-xl hover:bg-green-700'><Save size={20} /> ذخیره تغییرات</button></div>
        </div>
    );
};

export default ProfileTab;