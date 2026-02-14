import React, { useEffect, useRef, useState } from 'react';
import { CandidateData } from '../../types';
import { Save, Clock, ShieldAlert, AlertTriangle, Bot, Image as ImageIcon, Upload, Text } from 'lucide-react';
import BotPreview from '../BotPreview';
import { api } from '../../services/api';

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

interface TelegramProfileConfig {
    description: string;
    short_description: string;
}

const BotSettingsTab: React.FC<BotSettingsTabProps> = ({ candidate, onUpdate }) => {
    const buildConfig = (): BotConfig => (candidate.bot_config || {
        auto_lock_enabled: false,
        lock_start_time: '23:00',
        lock_end_time: '07:00',
        anti_link_enabled: false,
        forbidden_words: ''
    });

    const buildTelegramProfile = (): TelegramProfileConfig => {
        const bc: any = candidate.bot_config || {};
        const tp = bc.telegram_profile || bc.telegramProfile || {};
        return {
            description: typeof tp.description === 'string' ? tp.description : '',
            short_description:
                typeof tp.short_description === 'string'
                    ? tp.short_description
                    : (typeof tp.shortDescription === 'string' ? tp.shortDescription : ''),
        };
    };

    const [config, setConfig] = useState<BotConfig>(buildConfig());
    const [botName, setBotName] = useState<string>(candidate.bot_name || '');
    const [telegramProfile, setTelegramProfile] = useState<TelegramProfileConfig>(buildTelegramProfile());
    const [previewImage, setPreviewImage] = useState<string | null>(candidate.image_url || null);
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const lastCandidateIdRef = useRef<string | null>(candidate.id ?? null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const candidateId = candidate.id ?? null;
        const candidateChanged = candidateId !== lastCandidateIdRef.current;
        if (candidateChanged) {
            lastCandidateIdRef.current = candidateId;
        }

        // Avoid wiping user's in-progress edits due to App polling updates.
        if (candidateChanged || !isDirty) {
            setConfig(buildConfig());
            setBotName(candidate.bot_name || '');
            setTelegramProfile(buildTelegramProfile());
            setPreviewImage(candidate.image_url || null);
            setImageFile(null);
            setIsDirty(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [candidate.id, candidate.bot_config, candidate.bot_name, candidate.image_url, isDirty]);

    const handleConfigChange = (field: keyof BotConfig, value: any) => {
        setIsDirty(true);
        setConfig(prev => ({ ...prev, [field]: value }));
    };

    const handleTelegramProfileChange = (field: keyof TelegramProfileConfig, value: string) => {
        setIsDirty(true);
        setTelegramProfile(prev => ({ ...prev, [field]: value }));
    };

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setIsDirty(true);
        setImageFile(file);
        const reader = new FileReader();
        reader.onloadend = () => setPreviewImage(reader.result as string);
        reader.readAsDataURL(file);
    };

    const handleSave = async () => {
        const token = localStorage.getItem('access_token') || '';

        setIsSaving(true);
        try {
            let image_url = candidate.image_url;
            if (imageFile) {
                const data = await api.uploadFile(imageFile, token);
                image_url = data.url;
            }

            const nextBotConfig: any = {
                ...(candidate.bot_config || {}),
                ...config,
                telegram_profile: {
                    ...telegramProfile,
                },
            };

            await onUpdate({
                bot_name: botName,
                bot_config: nextBotConfig,
                image_url: image_url || undefined,
            });

            // Mark clean after persistence.
            setIsDirty(false);

            const tg = await api.applyTelegramProfile(candidate.id, token);
            if (tg?.ok === false) {
                const errs = tg?.errors || {};
                const messages = Object.values(errs).filter(Boolean);
                alert(messages.length ? String(messages.join('\n')) : 'اعمال روی تلگرام با خطا مواجه شد.');
                return;
            }

            const tgErrors = tg?.errors || {};
            const tgErrorMessages = Object.values(tgErrors).filter(Boolean);

            const tgNotes = tg?.notes || {};
            const tgNoteMessages = Object.values(tgNotes).filter(Boolean);

            const current = tg?.telegram || {};
            const currentSummary =
                (current?.name || current?.description || current?.short_description)
                    ? `\n\nوضعیت فعلی تلگرام:\nنام: ${current?.name || '—'}\nDescription: ${current?.description || '—'}\nShort: ${current?.short_description || '—'}`
                    : '';

            if (tgErrorMessages.length) {
                alert(`تنظیمات ذخیره شد، اما اعمال برخی موارد روی تلگرام خطا داد:\n${String(tgErrorMessages.join('\n'))}${currentSummary}`);
                return;
            }

            if (tgNoteMessages.length) {
                alert(`تنظیمات ذخیره و روی تلگرام اعمال شد.${currentSummary}\n\nنکته:\n${String(tgNoteMessages.join('\n'))}`);
                return;
            }

            alert(`تنظیمات ذخیره و روی تلگرام اعمال شد.${currentSummary}`);
        } catch (e: any) {
            alert(e?.message || 'خطا در ذخیره/اعمال تنظیمات بات');
        } finally {
            setIsSaving(false);
        }
    };

    const previewCandidate: CandidateData = {
        ...candidate,
        bot_name: botName || candidate.bot_name,
        image_url: (previewImage || candidate.image_url) as any,
        bot_config: {
            ...(candidate.bot_config || {}),
            ...config,
            telegram_profile: {
                ...telegramProfile,
            },
        } as any,
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-full overflow-hidden">

            {/* Right Column (Settings) */}
            <div className="lg:col-span-8 xl:col-span-9 flex flex-col gap-5 pt-4 h-full overflow-y-auto pr-1 order-2 lg:order-1 no-scrollbar">

                {/* Telegram Profile Section */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border shrink-0">
                    <div className="flex items-center gap-2 text-gray-800 font-bold text-sm mb-6">
                        <Bot size={18} className="text-blue-600" />
                        <h3>پروفایل بات در تلگرام</h3>
                    </div>

                    <div className="mb-6 bg-blue-50 border border-blue-100 rounded-xl p-4 text-right">
                        <div className="text-xs font-bold text-blue-700 mb-2">این تغییرات کجا دیده می‌شود؟</div>
                        <ul className="text-[11px] text-blue-700/90 leading-6 list-disc pr-4">
                            <li>نام/توضیحات: داخل صفحه اطلاعات بات در تلگرام (Info / Profile) و هدر چت.</li>
                            <li>عکس: داخل خود بات به‌صورت پیام (دکمه «عکس و پروفایل») ارسال می‌شود و در پیش‌نمایش دیده می‌شود.</li>
                            <li>نکته مهم: تغییر «آواتار واقعی بات در تلگرام» از طریق API ممکن نیست و باید با BotFather دستی تنظیم شود.</li>
                            <li>قفل خودکار/ضد لینک/کلمات ممنوعه: روی رفتار گروه‌ها اثر می‌گذارد (مدیریت پیام‌ها).</li>
                        </ul>
                        <div className="text-[10px] text-blue-700/80 mt-2">
                            برای دیدن پیش‌نمایش «پروفایل تلگرام»، روی آیکون (i) بالای موبایل بزنید.
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-2 text-right">نام نمایشی بات</label>
                            <input
                                value={botName}
                                onChange={(e) => {
                                    setIsDirty(true);
                                    setBotName(e.target.value);
                                }}
                                className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                placeholder="مثال: ستاد انتخاباتی ..."
                            />
                            <p className="text-[10px] text-gray-400 mt-2 text-right">
                                این مقدار هم در پیش‌نمایش و هم برای «نام بات در تلگرام» استفاده می‌شود.
                            </p>
                        </div>

                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-2 text-right">عکس نمایش داخل بات</label>
                            <div
                                className="border-2 border-dashed border-gray-200 rounded-2xl p-5 flex items-center justify-between bg-gray-50/50 hover:bg-gray-50 transition-colors cursor-pointer"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    accept="image/png, image/jpeg"
                                    onChange={handleImageUpload}
                                />
                                <div className="flex items-center gap-3">
                                    <div className="w-14 h-14 rounded-full overflow-hidden shadow-md bg-white border border-gray-200 flex items-center justify-center">
                                        {previewImage ? (
                                            <img src={previewImage} alt="Profile" className="w-full h-full object-cover" />
                                        ) : (
                                            <ImageIcon size={22} className="text-gray-400" />
                                        )}
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs font-bold text-gray-700">تغییر تصویر</p>
                                        <p className="text-[10px] text-gray-400">JPG, PNG (برای ارسال داخل چت)</p>
                                    </div>
                                </div>
                                <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-200">
                                    <Upload size={18} />
                                </div>
                            </div>
                        </div>

                        <div className="lg:col-span-2">
                            <div className="flex items-center gap-2 mb-2">
                                <Text size={14} className="text-gray-500" />
                                <label className="text-xs font-medium text-gray-500">توضیحات بات (Description)</label>
                            </div>
                            <textarea
                                value={telegramProfile.description}
                                onChange={(e) => handleTelegramProfileChange('description', e.target.value)}
                                className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none h-28"
                                placeholder="توضیحات بات که در پروفایل تلگرام نمایش داده می‌شود..."
                            />
                        </div>

                        <div className="lg:col-span-2">
                            <label className="block text-xs font-medium text-gray-500 mb-2 text-right">توضیح کوتاه (Short description)</label>
                            <input
                                value={telegramProfile.short_description}
                                onChange={(e) => handleTelegramProfileChange('short_description', e.target.value)}
                                className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                placeholder="یک جمله کوتاه..."
                            />
                        </div>
                    </div>
                </div>

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
                            disabled={isSaving}
                            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-colors shadow-lg text-xs font-bold ${isSaving ? 'bg-gray-300 text-gray-600 cursor-not-allowed shadow-gray-200' : 'bg-green-600 text-white hover:bg-green-700 shadow-green-200'}`}
                        >
                            <Save size={16} />
                            {isSaving ? 'در حال ذخیره...' : 'ذخیره و اعمال روی تلگرام'}
                        </button>
                    </div>
                </div>

            </div>

            {/* Left Column (Live Preview) */}
            <div className="lg:col-span-4 xl:col-span-3 flex flex-col order-1 lg:order-2 h-full min-h-0">
                <div className="bg-white p-4 rounded-2xl shadow-sm border h-full flex flex-col items-center overflow-hidden relative">
                    <div className="w-full bg-gray-50 rounded-2xl p-4 mb-2 flex flex-col items-center text-center border border-gray-100 shrink-0">
                        <div className="flex items-center gap-2 mb-1">
                            <Bot size={18} className="text-gray-600" />
                            <h3 className="font-bold text-gray-700 text-sm">پیش‌نمایش زنده بات</h3>
                        </div>
                        <p className="text-[10px] text-gray-400">قبل از ذخیره، تغییرات اینجا دیده می‌شود</p>
                    </div>

                    <div className="flex-1 w-full flex items-center justify-center overflow-hidden relative">
                        <div className="scale-[0.85] origin-center transform">
                            <BotPreview candidate={previewCandidate} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BotSettingsTab;
