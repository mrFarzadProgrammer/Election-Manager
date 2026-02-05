import React, { useState } from 'react';
import { CandidateData } from '../../types';
import { Save, Clock, ShieldAlert, AlertTriangle } from 'lucide-react';

interface BotSettingsTabProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

interface BotConfig {
    auto_lock_enabled: boolean;
    lock_start_time: string;
    lock_end_time: string;
    anti_link_enabled: boolean;
    forbidden_words: string;
}

const BotSettingsTab: React.FC<BotSettingsTabProps> = ({ candidate, onUpdate }) => {
    const initialConfig: BotConfig = candidate.bot_config || {
        auto_lock_enabled: false,
        lock_start_time: '23:00',
        lock_end_time: '07:00',
        anti_link_enabled: false,
        forbidden_words: ''
    };

    const [config, setConfig] = useState<BotConfig>(initialConfig);

    const handleConfigChange = (field: keyof BotConfig, value: any) => {
        setConfig(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        try {
            await onUpdate({
                ...candidate,
                bot_config: config
            });
            alert('تنظیمات بات با موفقیت ذخیره شد.');
        } catch (e: any) {
            alert(e?.message || 'خطا در ذخیره تنظیمات بات');
        }
    };

    return (
        <div className="h-full flex flex-col gap-5 pt-4 pr-1 overflow-hidden">

            {/* Group Time Management Section */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border shrink-0">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-2 text-gray-800 font-bold text-sm">
                            <Clock size={18} className="text-blue-600" />
                            <h3>مدیریت زمان گروه</h3>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="text-xs font-medium text-gray-600">فعال‌سازی قفل خودکار</span>
                        <button
                            onClick={() => handleConfigChange('auto_lock_enabled', !config.auto_lock_enabled)}
                            className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out ${config.auto_lock_enabled ? 'bg-blue-600' : 'bg-gray-200'}`}
                        >
                            <div className={`w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-200 ${config.auto_lock_enabled ? '-translate-x-6' : 'translate-x-0'}`} />
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-2 text-right">ساعت شروع قفل</label>
                        <input
                            type="time"
                            value={config.lock_start_time}
                            onChange={(e) => handleConfigChange('lock_start_time', e.target.value)}
                            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-center text-gray-700 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-2 text-right">ساعت پایان قفل</label>
                        <input
                            type="time"
                            value={config.lock_end_time}
                            onChange={(e) => handleConfigChange('lock_end_time', e.target.value)}
                            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-center text-gray-700 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        />
                    </div>
                </div>
                <p className="text-[10px] text-blue-400 bg-blue-50 p-2 rounded-lg text-center">
                    در ساعات مشخص شده، گروه به صورت خودکار بسته می‌شود و کسی نمی‌تواند پیام ارسال کند.
                </p>
            </div>

            {/* Filtering & Content Section */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border flex-1 flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-6 shrink-0">
                    <div className="flex items-center gap-2 text-gray-800 font-bold text-sm">
                        <ShieldAlert size={18} className="text-red-500" />
                        <h3>فیلترینگ و محتوا</h3>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <div className="flex items-center justify-between mb-6 bg-red-50 p-4 rounded-xl border border-red-100">
                        <span className="text-xs font-medium text-gray-700">جلوگیری از ارسال لینک (ضد تبلیغ)</span>
                        <button
                            onClick={() => handleConfigChange('anti_link_enabled', !config.anti_link_enabled)}
                            className={`w-12 h-6 rounded-full p-1 transition-colors duration-200 ease-in-out ${config.anti_link_enabled ? 'bg-red-500' : 'bg-gray-200'}`}
                        >
                            <div className={`w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-200 ${config.anti_link_enabled ? '-translate-x-6' : 'translate-x-0'}`} />
                        </button>
                    </div>

                    <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle size={14} className="text-orange-500" />
                            <label className="text-xs font-medium text-gray-500">کلمات ممنوعه (فیلتر فحاشی)</label>
                        </div>
                        <textarea
                            value={config.forbidden_words}
                            onChange={(e) => handleConfigChange('forbidden_words', e.target.value)}
                            className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 transition-all resize-none h-32"
                            placeholder="کلمات را با ویرگول جدا کنید (مثال: توهین, دروغ, فریب)..."
                        />
                    </div>
                    <p className="text-[10px] text-gray-400 text-center mb-4">
                        اگر کاربری از این کلمات استفاده کند، پیام او به صورت خودکار حذف می‌شود.
                    </p>
                </div>

                {/* Save Button */}
                <div className="flex justify-end mt-auto pt-4 border-t border-gray-100 shrink-0">
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
    );
};

export default BotSettingsTab;
