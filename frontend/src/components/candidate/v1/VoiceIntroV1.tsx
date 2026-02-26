import React, { useEffect, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Mic, Save, Upload, Trash2 } from 'lucide-react';
import { api } from '../../../services/api';
import { getLegacyAccessToken } from '../../../services/api';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface VoiceIntroV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

const MAX_SECONDS = 60;
const MAX_BYTES = 2 * 1024 * 1024;

const allowedVoiceExt = (name: string) => {
    const n = (name || '').toLowerCase().trim();
    return n.endsWith('.mp3') || n.endsWith('.ogg');
};

const VoiceIntroV1: React.FC<VoiceIntroV1Props> = ({ candidate, onUpdate }) => {
    const voiceInputRef = useRef<HTMLInputElement>(null);

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    const [voiceFile, setVoiceFile] = useState<File | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);

    const [voiceDurationSeconds, setVoiceDurationSeconds] = useState<number | null>(null);

    const [currentVoiceUrl, setCurrentVoiceUrl] = useState<string | undefined>(candidate.voice_url || (candidate.bot_config?.voice_url as any));
    const lastCandidateIdRef = useRef<string>(candidate.id);

    useEffect(() => {
        const candidateChanged = lastCandidateIdRef.current !== candidate.id;
        if (candidateChanged) {
            lastCandidateIdRef.current = candidate.id;
            setIsDirty(false);
        }

        if (!isDirty || candidateChanged) {
            setCurrentVoiceUrl(candidate.voice_url || (candidate.bot_config?.voice_url as any));
            setVoiceFile(null);
            setVoiceDurationSeconds(null);
        }
    }, [candidate, isDirty]);

    const pickFile = () => voiceInputRef.current?.click();

    const validateDuration = async (file: File) => {
        const objectUrl = URL.createObjectURL(file);
        try {
            const audio = new Audio(objectUrl);
            await new Promise<void>((resolve, reject) => {
                audio.addEventListener('loadedmetadata', () => resolve(), { once: true });
                audio.addEventListener('error', () => reject(new Error('خواندن فایل صوتی ناموفق بود')), { once: true });
            });

            if (Number.isFinite(audio.duration) && audio.duration > MAX_SECONDS) {
                throw new Error(`مدت ویس باید حداکثر ${MAX_SECONDS} ثانیه باشد. (الان: ${Math.ceil(audio.duration)} ثانیه)`);
            }

            if (Number.isFinite(audio.duration) && audio.duration > 0) {
                return Math.ceil(audio.duration);
            }
            return null;
        } finally {
            URL.revokeObjectURL(objectUrl);
        }
    };

    const validateVoiceFile = async (file: File) => {
        if (file.size > MAX_BYTES) {
            throw new Error('حجم فایل صوتی باید حداکثر ۲ مگابایت باشد.');
        }

        const type = (file.type || '').toLowerCase();
        const okByType = type.includes('audio/') || type === 'application/ogg' || type === '';
        if (!okByType) {
            throw new Error('نوع فایل معتبر نیست. فقط فایل صوتی مجاز است.');
        }

        if (!allowedVoiceExt(file.name)) {
            throw new Error('فرمت فایل صوتی باید mp3 یا ogg باشد.');
        }

        return await validateDuration(file);
    };

    const handleVoiceUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        try {
            const duration = await validateVoiceFile(file);
            setVoiceFile(file);
            setVoiceDurationSeconds(duration);
            setIsDirty(true);
        } catch (err: any) {
            setModal({ variant: 'warning', title: 'اعتبارسنجی', message: err?.message || 'فایل صوتی معتبر نیست' });
            e.target.value = '';
            setVoiceFile(null);
            setVoiceDurationSeconds(null);
        }
    };

    const handleDeleteCurrentVoice = async () => {
        if (!currentVoiceUrl && !(candidate.voice_url || (candidate.bot_config as any)?.voice_url)) {
            setModal({ variant: 'info', title: 'چیزی برای حذف نیست', message: 'ویسی ثبت نشده است.' });
            return;
        }

        const ok = window.confirm('ویس فعلی حذف شود؟');
        if (!ok) return;

        setIsSaving(true);
        try {
            const nextBotConfig: any = (candidate.bot_config && typeof candidate.bot_config === 'object') ? { ...(candidate.bot_config as any) } : {};
            if ('voice_url' in nextBotConfig) {
                delete nextBotConfig.voice_url;
            }

            await onUpdate({ voice_url: null as any, bot_config: nextBotConfig });

            setCurrentVoiceUrl(undefined);
            setVoiceFile(null);
            setIsDirty(false);
            setModal({ variant: 'success', title: 'حذف شد', message: 'ویس فعلی حذف شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در حذف', message: e?.message || 'حذف ویس ناموفق بود' });
        } finally {
            setIsSaving(false);
        }
    };

    const handleSave = async () => {
        const token = getLegacyAccessToken();

        if (!voiceFile) {
            setModal({ variant: 'warning', title: 'فایل انتخاب نشده', message: 'ابتدا یک فایل صوتی انتخاب کنید.' });
            return;
        }

        if (voiceFile.size > MAX_BYTES) {
            setModal({ variant: 'warning', title: 'حجم فایل', message: 'حجم فایل صوتی باید حداکثر ۲ مگابایت باشد.' });
            return;
        }

        if (!allowedVoiceExt(voiceFile.name)) {
            setModal({ variant: 'warning', title: 'فرمت فایل', message: 'فرمت فایل صوتی باید mp3 یا ogg باشد.' });
            return;
        }

        setIsSaving(true);
        try {
            const data = await api.uploadVoiceIntro(voiceFile, token, {
                candidate_name: candidate?.name || candidate?.full_name || '',
            });

            const voice_url = data.url;
            const bot_config = {
                ...(candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}),
                voice_url,
                voice_intro_duration: voiceDurationSeconds ?? undefined,
            };

            await onUpdate({ voice_url, bot_config });
            setCurrentVoiceUrl(voice_url);
            setVoiceFile(null);
            setVoiceDurationSeconds(null);
            setIsDirty(false);
            setModal({ variant: 'success', title: 'ذخیره شد', message: 'ویس با موفقیت ذخیره شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در ذخیره', message: e?.message || 'خطا در ذخیره' });
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
                    <Mic size={20} className="text-blue-600" />
                    معرفی صوتی
                </h3>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    <div className="lg:col-span-7">
                        <label className="block text-sm font-medium mb-2">آپلود ویس معرفی (حداکثر ۶۰ ثانیه)</label>
                        <div className="border border-gray-200 rounded-xl p-4 flex items-center justify-between bg-white">
                            <button
                                onClick={pickFile}
                                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors shadow-sm"
                            >
                                انتخاب فایل
                            </button>
                            <input
                                type="file"
                                ref={voiceInputRef}
                                className="hidden"
                                accept=".mp3,.ogg,audio/mpeg,audio/ogg"
                                onChange={handleVoiceUpload}
                            />

                            <div className="flex items-center gap-3">
                                <div className="text-right">
                                    <p className="text-xs font-bold text-gray-700">{voiceFile ? voiceFile.name : 'فایل صوتی'}</p>
                                    <p className="text-[10px] text-gray-400">
                                        {voiceFile ? `${(voiceFile.size / 1024 / 1024).toFixed(2)} MB${voiceDurationSeconds ? ` • ${voiceDurationSeconds}s` : ''}` : 'هنوز فایلی انتخاب نشده است'}
                                    </p>
                                </div>
                                <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-500">
                                    <Upload size={18} />
                                </div>
                            </div>
                        </div>
                        <p className="text-[11px] text-gray-400 mt-2">قوانین: حداکثر ۶۰ ثانیه، فقط mp3 یا ogg، حداکثر ۲MB.</p>

                        {voiceFile && (
                            <div className="mt-4 flex justify-end">
                                <button
                                    onClick={handleSave}
                                    disabled={isSaving}
                                    className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-colors ${isSaving ? 'bg-gray-300 text-gray-700' : 'bg-green-600 text-white hover:bg-green-700'}`}
                                >
                                    <Save size={18} />
                                    {isSaving ? 'در حال آپلود...' : 'تأیید و آپلود'}
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="lg:col-span-5">
                        <label className="block text-sm font-medium mb-2">پخش ویس فعلی</label>
                        <div className="border border-gray-200 rounded-xl p-4 bg-gray-50">
                            {currentVoiceUrl ? (
                                <div className="space-y-3">
                                    <audio controls className="w-full" src={currentVoiceUrl} />
                                    <button
                                        onClick={handleDeleteCurrentVoice}
                                        disabled={isSaving}
                                        className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-red-200 bg-white text-red-700 hover:bg-red-50 transition disabled:opacity-60"
                                        title="حذف ویس فعلی"
                                    >
                                        <Trash2 size={16} />
                                        حذف ویس فعلی
                                    </button>
                                </div>
                            ) : (
                                <p className="text-sm text-gray-500">ویسی ثبت نشده است.</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VoiceIntroV1;
