import React, { useEffect, useState } from 'react';
import { CandidateData } from '../../types';
import { Save, Bot } from 'lucide-react';
import BotPreview from '../BotPreview';

interface MyProgramsTabProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

const MyProgramsTab: React.FC<MyProgramsTabProps> = ({ candidate, onUpdate }) => {
    const [formData, setFormData] = useState<CandidateData>(candidate);

    useEffect(() => {
        setFormData(candidate);
    }, [candidate]);

    const handleChange = (field: keyof CandidateData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        try {
            await onUpdate(formData);
            alert('تغییرات با موفقیت ذخیره شد.');
        } catch (e: any) {
            alert(e?.message || 'خطا در ذخیره تغییرات');
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-full overflow-hidden">
            {/* Right Column (Forms) */}
            <div className="lg:col-span-8 xl:col-span-9 flex flex-col gap-5 pt-4 h-full overflow-y-auto pr-1 order-2 lg:order-1 no-scrollbar">

                <div className="bg-white p-6 rounded-2xl shadow-sm border flex-1 flex flex-col">
                    <h3 className="text-sm font-bold mb-6 text-gray-800 text-right">محتوای تبلیغاتی</h3>

                    {/* Slogan Section */}
                    <div className="mb-6">
                        <label className="block text-xs font-medium text-gray-500 mb-2 text-right">شعار انتخاباتی</label>
                        <input
                            type="text"
                            value={formData.slogan || ''}
                            onChange={(e) => handleChange('slogan', e.target.value)}
                            className="w-full p-4 bg-blue-50/50 border border-blue-100 rounded-xl text-center text-blue-800 font-bold text-lg focus:outline-none focus:ring-2 focus:ring-blue-200 transition-all placeholder-blue-300"
                            placeholder="شعار انتخاباتی خود را وارد کنید..."
                        />
                    </div>

                    {/* Resume Section */}
                    <div className="mb-6">
                        <label className="block text-xs font-medium text-gray-500 mb-2 text-right">رزومه و سوابق</label>
                        <textarea
                            value={formData.resume || ''}
                            onChange={(e) => handleChange('resume', e.target.value)}
                            className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none h-32"
                            placeholder="سوابق تحصیلی و شغلی خود را بنویسید..."
                        />
                    </div>

                    {/* Ideas Section */}
                    <div className="mb-6">
                        <label className="block text-xs font-medium text-gray-500 mb-2 text-right">ایده‌ها و برنامه‌ها</label>
                        <textarea
                            value={formData.ideas || ''}
                            onChange={(e) => handleChange('ideas', e.target.value)}
                            className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none h-32"
                            placeholder="برنامه‌های خود را برای آینده شرح دهید..."
                        />
                    </div>

                    {/* Save Button */}
                    <div className="flex justify-end mt-auto">
                        <button
                            onClick={handleSave}
                            className="flex items-center gap-2 bg-green-600 text-white px-6 py-2.5 rounded-xl hover:bg-green-700 transition-colors shadow-lg shadow-green-200 text-xs font-bold"
                        >
                            <Save size={16} />
                            ذخیره تغییرات
                        </button>
                    </div>
                </div>
            </div>

            {/* Left Column (Bot Preview) */}
            <div className="lg:col-span-4 xl:col-span-3 flex flex-col order-1 lg:order-2 h-full min-h-0">
                <div className="bg-white p-4 rounded-2xl shadow-sm border h-full flex flex-col items-center overflow-hidden relative">

                    {/* Header Section */}
                    <div className="w-full bg-gray-50 rounded-2xl p-4 mb-2 flex flex-col items-center text-center border border-gray-100 shrink-0">
                        <div className="flex items-center gap-2 mb-1">
                            <Bot size={18} className="text-gray-600" />
                            <h3 className="font-bold text-gray-700 text-sm">پیش‌نمایش زنده بات</h3>
                        </div>
                        <p className="text-[10px] text-gray-400">تغییرات شما به صورت آنی در اینجا نمایش داده می‌شود</p>
                    </div>

                    {/* Phone Mockup Container */}
                    <div className="flex-1 w-full flex items-center justify-center overflow-hidden relative">
                        <div className="scale-[0.85] origin-center transform">
                            <BotPreview candidate={formData} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MyProgramsTab;
