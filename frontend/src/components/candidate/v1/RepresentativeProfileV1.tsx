import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Save, User } from 'lucide-react';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface RepresentativeProfileV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

const MAX_SLOGAN = 500;

const RepresentativeProfileV1: React.FC<RepresentativeProfileV1Props> = ({ candidate, onUpdate }) => {
    const initialBotConfig = useMemo(() => (candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}), [candidate.bot_config]);
    const initialSocials = useMemo(() => (candidate.socials && typeof candidate.socials === 'object' ? candidate.socials : {}), [candidate.socials]);

    const [fullName, setFullName] = useState(candidate.full_name || candidate.name || '');
    const [constituency, setConstituency] = useState(String(candidate.constituency ?? (initialBotConfig as any).constituency ?? ''));
    const [slogan, setSlogan] = useState(candidate.slogan || '');

    const [telegramChannel, setTelegramChannel] = useState(String((initialSocials as any).telegram_channel ?? (initialSocials as any).telegramChannel ?? ''));
    const [telegramGroup, setTelegramGroup] = useState(String((initialSocials as any).telegram_group ?? (initialSocials as any).telegramGroup ?? ''));

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
        }
    }, [candidate, isDirty]);

    const normalizeSlogan = (raw: string) => {
        const lines = (raw || '')
            .replace(/\r\n/g, '\n')
            .split('\n')
            .map((x) => x.trim())
            .filter(Boolean);
        return lines.join('\n');
    };

    const handleSave = async () => {
        const normalizedSlogan = normalizeSlogan(slogan);
        if (normalizedSlogan.length > MAX_SLOGAN) {
            setModal({ variant: 'warning', title: 'اعتبارسنجی', message: `مجموع شعارها حداکثر ${MAX_SLOGAN} کاراکتر است.` });
            return;
        }

        setIsSaving(true);
        try {
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
                slogan: normalizedSlogan || undefined,
                socials,
                bot_config,
            });

            setIsDirty(false);
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

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                                <span className={`text-xs ${normalizeSlogan(slogan).length > MAX_SLOGAN ? 'text-red-600' : 'text-gray-400'}`}>{normalizeSlogan(slogan).length}/{MAX_SLOGAN}</span>
                            </div>
                            <textarea
                                value={slogan}
                                onChange={(e) => {
                                    setSlogan(e.target.value);
                                    setIsDirty(true);
                                }}
                                className="border rounded-xl px-4 py-2 resize-none h-24"
                                placeholder="هر خط یک شعار جداست (Enter برای خط جدید)"
                            />
                            {normalizeSlogan(slogan) ? (
                                <div className="mt-2 flex flex-wrap gap-2">
                                    {normalizeSlogan(slogan)
                                        .split('\n')
                                        .map((line, idx) => (
                                            <span key={idx} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-100">
                                                «{line}»
                                            </span>
                                        ))}
                                </div>
                            ) : (
                                <p className="text-[11px] text-gray-400">پیش‌نمایش شعارها اینجا نمایش داده می‌شود.</p>
                            )}
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
