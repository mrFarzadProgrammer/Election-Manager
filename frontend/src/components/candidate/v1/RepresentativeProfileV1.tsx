import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Save, Upload, Image as ImageIcon, User } from 'lucide-react';
import { api } from '../../../services/api';
import { getLegacyAccessToken } from '../../../services/api';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface RepresentativeProfileV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

const MAX_SLOGAN = 120;

const RepresentativeProfileV1: React.FC<RepresentativeProfileV1Props> = ({ candidate, onUpdate }) => {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const initialBotConfig = useMemo(() => (candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}), [candidate.bot_config]);
    const initialSocials = useMemo(() => (candidate.socials && typeof candidate.socials === 'object' ? candidate.socials : {}), [candidate.socials]);

    const [fullName, setFullName] = useState(candidate.full_name || candidate.name || '');
    const [constituency, setConstituency] = useState(String(candidate.constituency ?? (initialBotConfig as any).constituency ?? ''));
    const [slogan, setSlogan] = useState(candidate.slogan || '');

    const [telegramChannel, setTelegramChannel] = useState(String((initialSocials as any).telegram_channel ?? (initialSocials as any).telegramChannel ?? ''));
    const [telegramGroup, setTelegramGroup] = useState(String((initialSocials as any).telegram_group ?? (initialSocials as any).telegramGroup ?? ''));

    const [previewImage, setPreviewImage] = useState<string | null>(candidate.image_url || null);
    const [imageFile, setImageFile] = useState<File | null>(null);

    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const lastCandidateIdRef = useRef<string>(candidate.id);

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    useEffect(() => {
        const candidateChanged = lastCandidateIdRef.current !== candidate.id;
        if (candidateChanged) {
            lastCandidateIdRef.current = candidate.id;
            setIsDirty(false);
        }

        if (!isDirty || candidateChanged) {
            const botConfig = candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {};
            const socials = candidate.socials && typeof candidate.socials === 'object' ? candidate.socials : {};
            setFullName(candidate.full_name || candidate.name || '');
            setConstituency(String(candidate.constituency ?? (botConfig as any).constituency ?? ''));
            setSlogan(candidate.slogan || '');
            setTelegramChannel(String((socials as any).telegram_channel ?? (socials as any).telegramChannel ?? ''));
            setTelegramGroup(String((socials as any).telegram_group ?? (socials as any).telegramGroup ?? ''));
            setPreviewImage(candidate.image_url || null);
            setImageFile(null);
        }
    }, [candidate, isDirty]);

    const handleImagePick = () => fileInputRef.current?.click();

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
        const token = getLegacyAccessToken();

        const trimmedSlogan = (slogan || '').trim();
        if (trimmedSlogan.length > MAX_SLOGAN) {
            setModal({ variant: 'warning', title: 'اعتبارسنجی', message: `شعار حداکثر ${MAX_SLOGAN} کاراکتر است.` });
            return;
        }

        setIsSaving(true);
        try {
            let image_url = candidate.image_url;

            if (imageFile) {
                const data = await api.uploadFile(imageFile, token);
                image_url = data.url;
            }

            const trimmedConstituency = (constituency || '').trim();
            const bot_config = {
                ...(candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}),
                // Keep mirror for older bot/UI paths
                constituency: trimmedConstituency,
            };

            const trimmedTelegramChannel = (telegramChannel || '').trim();
            const trimmedTelegramGroup = (telegramGroup || '').trim();
            const socials = {
                ...(candidate.socials && typeof candidate.socials === 'object' ? candidate.socials : {}),
                telegram_channel: trimmedTelegramChannel || undefined,
                telegram_group: trimmedTelegramGroup || undefined,
            };

            await onUpdate({
                name: (fullName || '').trim(),
                constituency: trimmedConstituency,
                slogan: trimmedSlogan,
                image_url: image_url || undefined,
                socials,
                bot_config,
            });

            setIsDirty(false);
            setImageFile(null);
            setModal({ variant: 'success', title: 'ذخیره شد', message: 'تغییرات با موفقیت ذخیره شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در ذخیره', message: e?.message || 'خطا در ذخیره اطلاعات' });
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <ResultModal
                open={!!modal}
                variant={modal?.variant || 'info'}
                title={modal?.title || ''}
                message={modal?.message || ''}
                onClose={() => setModal(null)}
            />
            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <User size={20} className="text-blue-600" />
                    پروفایل نماینده
                </h3>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    <div className="lg:col-span-4">
                        <label className="block text-sm font-medium mb-2">عکس پروفایل</label>
                        <div
                            className="border-2 border-dashed border-gray-200 rounded-2xl p-6 flex flex-col items-center justify-center bg-gray-50/50 hover:bg-gray-50 transition-colors cursor-pointer"
                            onClick={handleImagePick}
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="hidden"
                                accept="image/png, image/jpeg"
                                onChange={handleImageUpload}
                            />

                            <div className="w-24 h-24 rounded-full overflow-hidden mb-3 shadow-md relative group">
                                {previewImage ? (
                                    <img src={previewImage} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full bg-gray-200 flex items-center justify-center text-gray-400">
                                        <ImageIcon size={32} />
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Upload size={20} className="text-white" />
                                </div>
                            </div>

                            <span className="text-xs font-bold text-gray-600 mb-1">تغییر تصویر</span>
                            <span className="text-[10px] text-gray-400">JPG, PNG</span>
                        </div>
                    </div>

                    <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium">نام و نام خانوادگی</label>
                            <input
                                value={fullName}
                                onChange={(e) => {
                                    setFullName(e.target.value);
                                    setIsDirty(true);
                                }}
                                className="border rounded-xl px-4 py-2"
                                placeholder="مثلاً: رضا تبریزی"
                            />
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium">حوزه انتخابیه</label>
                            <input
                                value={constituency}
                                onChange={(e) => {
                                    setConstituency(e.target.value);
                                    setIsDirty(true);
                                }}
                                className="border rounded-xl px-4 py-2"
                                placeholder="مثلاً: تهران"
                            />
                            <p className="text-[11px] text-gray-400">این مقدار در بات نمایش داده می‌شود.</p>
                        </div>

                        <div className="flex flex-col gap-2 md:col-span-2">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium">شعار انتخاباتی</label>
                                <span className={`text-xs ${slogan.length > MAX_SLOGAN ? 'text-red-600' : 'text-gray-400'}`}>{slogan.length}/{MAX_SLOGAN}</span>
                            </div>
                            <input
                                value={slogan}
                                maxLength={MAX_SLOGAN}
                                onChange={(e) => {
                                    setSlogan(e.target.value);
                                    setIsDirty(true);
                                }}
                                className="border rounded-xl px-4 py-2"
                                placeholder="حداکثر ۱۲۰ کاراکتر"
                            />
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium">آدرس کانال تلگرام</label>
                            <input
                                value={telegramChannel}
                                onChange={(e) => {
                                    setTelegramChannel(e.target.value);
                                    setIsDirty(true);
                                }}
                                className="border rounded-xl px-4 py-2"
                                placeholder="مثلاً: https://t.me/MyChannel یا @MyChannel"
                                dir="ltr"
                            />
                            <p className="text-[11px] text-gray-400">در پیام‌های بات برای دریافت جمع‌بندی‌ها نمایش داده می‌شود.</p>
                        </div>

                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium">آدرس گروه تلگرام</label>
                            <input
                                value={telegramGroup}
                                onChange={(e) => {
                                    setTelegramGroup(e.target.value);
                                    setIsDirty(true);
                                }}
                                className="border rounded-xl px-4 py-2"
                                placeholder="مثلاً: https://t.me/MyGroup یا @MyGroup"
                                dir="ltr"
                            />
                            <p className="text-[11px] text-gray-400">اختیاری است؛ در صورت نیاز می‌توانید خالی بگذارید.</p>
                        </div>
                    </div>
                </div>

                <div className="flex justify-end mt-6">
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className={`flex items-center gap-2 px-8 py-3 rounded-xl transition-colors ${isSaving ? 'bg-gray-300 text-gray-700' : 'bg-green-600 text-white hover:bg-green-700'}`}
                    >
                        <Save size={18} />
                        {isSaving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default RepresentativeProfileV1;
