import React, { useState } from 'react';
import { CandidateData, Plan, Announcement } from '../../types';
import { Save, Share, Users, MapPin, Link as LinkIcon, Instagram, Send, ExternalLink, Bot, CreditCard, Megaphone } from 'lucide-react';
import BotPreview from '../BotPreview';
import QuotesCarousel from '../QuotesCarousel';

interface InfoStatsTabProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
    plans: Plan[];
    announcements: Announcement[];
}

const InfoStatsTab: React.FC<InfoStatsTabProps> = ({ candidate, onUpdate, plans, announcements }) => {
    const [formData, setFormData] = useState<CandidateData>(candidate);
    const [socials, setSocials] = useState<{ telegram_channel?: string; telegram_group?: string; instagram?: string }>(
        candidate.socials || {}
    );

    const activePlan = plans.find(p => p.id.toString() === candidate.active_plan_id?.toString());
    const recentAnnouncements = announcements.slice(0, 2);

    const handleChange = (field: keyof CandidateData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSocialChange = (key: string, value: string) => {
        setSocials(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        try {
            await onUpdate({
                ...formData,
                socials: socials
            });
            alert('تغییرات با موفقیت ذخیره شد.');
        } catch (e: any) {
            alert(e?.message || 'خطا در ذخیره تغییرات');
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-full overflow-hidden">
            {/* Right Column (Forms & Stats) */}
            <div className="lg:col-span-8 xl:col-span-9 flex flex-col gap-5 pt-4 overflow-y-auto pr-1 order-2 lg:order-1 no-scrollbar">
                {/* Quote Banner */}
                <div className="h-32 shrink-0 rounded-2xl overflow-hidden shadow-sm">
                    <QuotesCarousel variant="widget" />
                </div>

                {/* Stats Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2 shrink-0">
                    {/* Fan Count */}
                    <div className="bg-blue-600 text-white p-3 rounded-2xl shadow-sm flex items-center justify-between relative overflow-hidden h-24">
                        <div className="relative z-10 flex flex-col justify-between h-full">
                            <p className="text-blue-100 text-xs">تعداد هواداران</p>
                            <p className="font-bold text-2xl">{formData.vote_count || 0}</p>
                        </div>
                        <div className="p-2 bg-white/20 rounded-2xl text-white relative z-10">
                            <Users size={20} />
                        </div>
                        <div className="absolute -left-6 -bottom-6 text-white/10">
                            <Users size={80} />
                        </div>
                    </div>

                    {/* Active Plan */}
                    <div className="bg-white p-3 rounded-2xl shadow-sm border flex flex-col justify-between h-24 relative overflow-hidden">
                        <div className="flex justify-between items-start">
                            <p className="text-gray-400 text-[10px]">پلن فعال</p>
                            <CreditCard size={16} className="text-gray-300" />
                        </div>
                        <div>
                            <p className="font-bold text-gray-800 text-sm truncate">{activePlan?.title || 'بدون پلن'}</p>
                            <p className="text-[10px] text-gray-400 mt-1">
                                {candidate.plan_expires_at ? `انقضا: ${new Date(candidate.plan_expires_at).toLocaleDateString('fa-IR')}` : 'نامحدود'}
                            </p>
                        </div>
                        {activePlan && <div className="absolute bottom-0 left-0 right-0 h-1" style={{ backgroundColor: activePlan.color }}></div>}
                    </div>

                    {/* Recent Announcement */}
                    <div className="bg-white p-3 rounded-2xl shadow-sm border flex flex-col justify-between h-24 relative overflow-hidden lg:col-span-2">
                        <div className="flex justify-between items-center mb-2">
                            <p className="text-gray-400 text-[10px] flex items-center gap-1">
                                <Megaphone size={12} />
                                آخرین اطلاعیه
                            </p>
                        </div>
                        {recentAnnouncements.length > 0 ? (
                            <div className="space-y-2">
                                {recentAnnouncements.map(ann => (
                                    <div key={ann.id} className="flex items-center gap-2 text-xs text-gray-600 truncate">
                                        <span className="w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0"></span>
                                        <span className="truncate">{ann.title}</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-gray-400 text-center">اطلاعیه‌ای نیست</p>
                        )}
                    </div>
                </div>

                {/* Combined Form Card */}
                <div className="bg-white p-4 rounded-2xl shadow-sm border shrink-0">
                    <h3 className="text-xs font-bold mb-4 text-gray-800">اطلاعات پایه</h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        {/* Row 1 */}
                        <div className="space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">نام کامل</label>
                            <input
                                value={formData.name}
                                onChange={(e) => handleChange('name', e.target.value)}
                                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50"
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">شهر</label>
                            <input
                                value={formData.city || ''}
                                onChange={(e) => handleChange('city', e.target.value)}
                                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50"
                            />
                        </div>

                        {/* Row 2 */}
                        <div className="space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">استان</label>
                            <input
                                value={formData.province || ''}
                                onChange={(e) => handleChange('province', e.target.value)}
                                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50"
                            />
                        </div>
                        <div className="hidden md:block"></div> {/* Spacer */}

                        {/* Row 3: Address */}
                        <div className="md:col-span-2 space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">آدرس ستاد انتخاباتی</label>
                            <div className="relative">
                                <input
                                    value={formData.address || ''}
                                    onChange={(e) => handleChange('address', e.target.value)}
                                    className="w-full border border-gray-200 rounded-xl px-3 py-2 pr-8 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50"
                                />
                                <MapPin size={16} className="absolute right-2.5 top-1/2 transform -translate-y-1/2 text-gray-400" />
                            </div>
                        </div>
                    </div>

                    <h3 className="text-xs font-bold mb-4 text-gray-800 flex items-center gap-2">
                        <LinkIcon size={16} className="transform -rotate-45" />
                        شبکه‌های اجتماعی
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        {/* Row 4 */}
                        <div className="space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">کانال تلگرام</label>
                            <div className="relative">
                                <input
                                    value={socials.telegram_channel || ''}
                                    onChange={(e) => handleSocialChange('telegram_channel', e.target.value)}
                                    placeholder="https://t.me/your_channel"
                                    className="w-full border border-gray-200 rounded-xl px-3 py-2 pl-8 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50 dir-ltr text-left placeholder:text-gray-300"
                                />
                                <Send size={16} className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-blue-400" />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">گروه تلگرام</label>
                            <div className="relative">
                                <input
                                    value={socials.telegram_group || ''}
                                    onChange={(e) => handleSocialChange('telegram_group', e.target.value)}
                                    placeholder="https://t.me/your_group"
                                    className="w-full border border-gray-200 rounded-xl px-3 py-2 pl-8 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50 dir-ltr text-left placeholder:text-gray-300"
                                />
                                <Users size={16} className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-blue-400" />
                            </div>
                        </div>

                        {/* Row 5 */}
                        <div className="space-y-1">
                            <label className="text-[10px] font-medium text-gray-500">اینستاگرام</label>
                            <div className="relative">
                                <input
                                    value={socials.instagram || ''}
                                    onChange={(e) => handleSocialChange('instagram', e.target.value)}
                                    placeholder="https://instagram.com/your_profile"
                                    className="w-full border border-gray-200 rounded-xl px-3 py-2 pl-8 text-xs focus:ring-1 focus:ring-blue-500 outline-none bg-gray-50/50 dir-ltr text-left placeholder:text-gray-300"
                                />
                                <Instagram size={16} className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-pink-500" />
                            </div>
                        </div>
                    </div>

                    {/* Save Button inside the card */}
                    <div className="mt-2 flex justify-end">
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

export default InfoStatsTab;
