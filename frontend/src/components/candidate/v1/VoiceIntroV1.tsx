import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Mic, Save, Upload, Square, Trash2 } from 'lucide-react';
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

const pickRecordingMimeType = () => {
    // MVP hard constraint: store mp3/ogg. Recording is allowed only if browser can produce ogg.
    const candidates = ['audio/ogg;codecs=opus', 'audio/ogg'];
    const mrAny: any = (window as any).MediaRecorder;
    if (!mrAny?.isTypeSupported) return '';
    for (const t of candidates) {
        try {
            if (mrAny.isTypeSupported(t)) return t;
        } catch {
            // ignore
        }
    }
    return '';
};

const extFromMime = (mime: string) => {
    if (mime.includes('ogg')) return 'ogg';
    if (mime.includes('mpeg') || mime.includes('mp3')) return 'mp3';
    return 'ogg';
};

const VoiceIntroV1: React.FC<VoiceIntroV1Props> = ({ candidate, onUpdate }) => {
    const voiceInputRef = useRef<HTMLInputElement>(null);

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    const [voiceFile, setVoiceFile] = useState<File | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);

    const [voiceDurationSeconds, setVoiceDurationSeconds] = useState<number | null>(null);

    const [isRecording, setIsRecording] = useState(false);
    const [isStopping, setIsStopping] = useState(false);
    const [recordSeconds, setRecordSeconds] = useState(0);
    const recordStartAtRef = useRef<number | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const recordChunksRef = useRef<BlobPart[]>([]);
    const recordStreamRef = useRef<MediaStream | null>(null);
    const [recordError, setRecordError] = useState<string | null>(null);
    const [recordPreviewUrl, setRecordPreviewUrl] = useState<string | null>(null);
    const recordMimeType = useMemo(() => pickRecordingMimeType(), []);

    const [currentVoiceUrl, setCurrentVoiceUrl] = useState<string | undefined>(candidate.voice_url || (candidate.bot_config?.voice_url as any));
    const lastCandidateIdRef = useRef<string>(candidate.id);

    useEffect(() => {
        // While recording, the app may refresh/poll candidate data in the background.
        // Avoid syncing/resetting local recorder state in that case, otherwise the timer
        // appears to reset (e.g., every 5 seconds) and recording becomes unusable.
        if (isRecording || isStopping) return;
        if (mediaRecorderRef.current || recordStreamRef.current) return;

        const candidateChanged = lastCandidateIdRef.current !== candidate.id;
        if (candidateChanged) {
            lastCandidateIdRef.current = candidate.id;
            setIsDirty(false);
        }

        if (!isDirty || candidateChanged) {
            setCurrentVoiceUrl(candidate.voice_url || (candidate.bot_config?.voice_url as any));
            setVoiceFile(null);
            setVoiceDurationSeconds(null);
            setRecordError(null);
            setRecordSeconds(0);
            recordStartAtRef.current = null;
            if (recordPreviewUrl) {
                URL.revokeObjectURL(recordPreviewUrl);
                setRecordPreviewUrl(null);
            }
        }
    }, [candidate, isDirty, isRecording, isStopping, recordPreviewUrl]);

    useEffect(() => {
        if (!isRecording) return;
        if (!recordStartAtRef.current) recordStartAtRef.current = Date.now();
        const t = window.setInterval(() => {
            const startAt = recordStartAtRef.current;
            if (!startAt) return;
            setRecordSeconds(Math.floor((Date.now() - startAt) / 1000));
        }, 250);
        return () => window.clearInterval(t);
    }, [isRecording]);

    useEffect(() => {
        if (!isRecording) return;
        if (recordSeconds >= MAX_SECONDS) {
            void stopRecording();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [recordSeconds, isRecording]);

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

        if (isRecording || isStopping) {
            setModal({ variant: 'warning', title: 'ضبط فعال است', message: 'ابتدا ضبط را متوقف کنید.' });
            e.target.value = '';
            return;
        }

        try {
            const duration = await validateVoiceFile(file);
            if (recordPreviewUrl) {
                URL.revokeObjectURL(recordPreviewUrl);
                setRecordPreviewUrl(null);
            }
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

    const startRecording = async () => {
        if (isRecording || isStopping) return;
        setRecordError(null);
        setIsStopping(false);
        if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
            setRecordError('مرورگر شما ضبط صدا را پشتیبانی نمی‌کند.');
            return;
        }
        if (!(window as any).MediaRecorder) {
            setRecordError('MediaRecorder در این مرورگر موجود نیست.');
            return;
        }

        if (!recordMimeType) {
            setRecordError('مرورگر شما خروجی ogg برای ضبط تولید نمی‌کند. لطفاً فایل mp3/ogg آپلود کنید.');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recordStreamRef.current = stream;
            recordChunksRef.current = [];
            setRecordSeconds(0);
            recordStartAtRef.current = Date.now();

            const mr = new MediaRecorder(stream, recordMimeType ? { mimeType: recordMimeType } : undefined);
            mediaRecorderRef.current = mr;

            mr.ondataavailable = (ev: BlobEvent) => {
                if (ev.data && ev.data.size > 0) recordChunksRef.current.push(ev.data);
            };

            mr.onerror = () => {
                setRecordError('خطا در ضبط صدا');
            };

            mr.onstop = async () => {
                try {
                    const mime = mr.mimeType || recordMimeType || 'audio/ogg';
                    const blob = new Blob(recordChunksRef.current, { type: mime });

                    if (!blob.size) {
                        throw new Error('هیچ صدایی ضبط نشد. دوباره تلاش کنید.');
                    }

                    const ext = extFromMime(mime);
                    const file = new File([blob], `voice-intro.${ext}`, { type: mime });

                    // We already enforce MAX_SECONDS by stopping the recorder, so duration validation is best-effort.
                    // Some browsers struggle to read metadata for recorded blobs; don't block the flow unless it's clearly too long.
                    let duration: number | null = null;
                    try {
                        duration = await validateVoiceFile(file);
                    } catch (e: any) {
                        const msg = String(e?.message || '');
                        if (msg.includes('حداکثر') || msg.includes(String(MAX_SECONDS))) {
                            throw e;
                        }
                    }

                    if (recordPreviewUrl) URL.revokeObjectURL(recordPreviewUrl);
                    setRecordPreviewUrl(URL.createObjectURL(blob));
                    setVoiceFile(file);
                    const fallbackDuration = recordSeconds ? Math.min(recordSeconds, MAX_SECONDS) : null;
                    setVoiceDurationSeconds(duration ?? fallbackDuration);
                    setIsDirty(true);
                } catch (e: any) {
                    setRecordError(e?.message || 'ویس ضبط‌شده معتبر نیست');
                } finally {
                    setIsStopping(false);
                    recordStartAtRef.current = null;
                    // cleanup stream tracks
                    try {
                        recordStreamRef.current?.getTracks()?.forEach((t) => t.stop());
                    } catch {
                        // ignore
                    }
                    recordStreamRef.current = null;
                    mediaRecorderRef.current = null;
                    recordChunksRef.current = [];
                }
            };

            // Use timeslice to force periodic dataavailable events (more reliable across browsers).
            mr.start(250);
            setIsRecording(true);
        } catch (e: any) {
            setRecordError(e?.message || 'اجازه دسترسی به میکروفون داده نشد');
        }
    };

    const stopRecording = async () => {
        if (isStopping) return;
        if (!isRecording && !mediaRecorderRef.current) return;
        setIsStopping(true);
        setIsRecording(false);
        try {
            const mr = mediaRecorderRef.current;
            if (mr && mr.state !== 'inactive') {
                // Best-effort: request last chunk before stopping.
                try {
                    (mr as any).requestData?.();
                } catch {
                    // ignore
                }
                mr.stop();
                return;
            }

            // If recorder is missing or already inactive, cleanup stream immediately.
            try {
                recordStreamRef.current?.getTracks()?.forEach((t) => t.stop());
            } catch {
                // ignore
            }
            recordStreamRef.current = null;
            mediaRecorderRef.current = null;
            recordChunksRef.current = [];
            recordStartAtRef.current = null;
            setIsStopping(false);
        } catch {
            // ignore
            setIsStopping(false);
        }
    };

    const discardRecording = () => {
        setRecordError(null);
        setRecordSeconds(0);
        recordStartAtRef.current = null;
        if (recordPreviewUrl) {
            URL.revokeObjectURL(recordPreviewUrl);
        }
        setRecordPreviewUrl(null);
        setVoiceFile(null);
        setVoiceDurationSeconds(null);
        setIsDirty(true);
    };

    const handleDeleteCurrentVoice = async () => {
        if (!currentVoiceUrl && !(candidate.voice_url || (candidate.bot_config as any)?.voice_url)) {
            setModal({ variant: 'info', title: 'چیزی برای حذف نیست', message: 'ویسی ثبت نشده است.' });
            return;
        }

        if (isRecording) {
            setModal({ variant: 'warning', title: 'ضبط فعال است', message: 'ابتدا ضبط را متوقف کنید.' });
            return;
        }

        if (isStopping) {
            setModal({ variant: 'info', title: 'در حال آماده‌سازی', message: 'لطفاً چند لحظه صبر کنید.' });
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
            setRecordError(null);
            setRecordSeconds(0);
            recordStartAtRef.current = null;
            if (recordPreviewUrl) {
                URL.revokeObjectURL(recordPreviewUrl);
                setRecordPreviewUrl(null);
            }
            setModal({ variant: 'success', title: 'حذف شد', message: 'ویس فعلی حذف شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در حذف', message: e?.message || 'حذف ویس ناموفق بود' });
        } finally {
            setIsSaving(false);
        }
    };

    const handleSave = async () => {
        const token = getLegacyAccessToken();

        if (isRecording) {
            setModal({ variant: 'warning', title: 'ضبط فعال است', message: 'ابتدا ضبط را متوقف کنید.' });
            return;
        }

        if (isStopping) {
            setModal({ variant: 'info', title: 'در حال آماده‌سازی', message: 'لطفاً چند لحظه صبر کنید تا ویس آماده شود.' });
            return;
        }

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

                <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4 mb-4">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div>
                            <p className="text-sm font-bold text-gray-700">ضبط مستقیم ویس (حداکثر ۶۰ ثانیه)</p>
                            <p className="text-[11px] text-gray-400 mt-1">
                                نکته: ضبط صدا در مرورگرهای جدید و روی localhost قابل استفاده است.
                            </p>
                        </div>

                        <div className="flex items-center gap-2">
                            {!isRecording ? (
                                <button
                                    onClick={startRecording}
                                    disabled={isStopping || !recordMimeType}
                                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 text-white hover:bg-red-700 transition"
                                >
                                    <Mic size={16} />
                                    شروع ضبط
                                </button>
                            ) : (
                                <button
                                    onClick={() => void stopRecording()}
                                    disabled={isStopping}
                                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-900 text-white hover:bg-black transition"
                                >
                                    <Square size={16} />
                                    توقف
                                </button>
                            )}

                            <div className={`text-sm font-bold ${isRecording ? 'text-red-600' : 'text-gray-500'}`}>⏱ {recordSeconds}s{isStopping ? '…' : ''}</div>

                            {(recordPreviewUrl || voiceFile) && !isRecording && (
                                <button
                                    onClick={discardRecording}
                                    disabled={isStopping}
                                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition"
                                    title="حذف ویس انتخاب‌شده"
                                >
                                    <Trash2 size={16} />
                                    حذف
                                </button>
                            )}
                        </div>
                    </div>

                    {recordError && <p className="text-xs text-red-600 mt-3">{recordError}</p>}
                    {!recordError && !recordMimeType && (
                        <p className="text-xs text-amber-700 mt-3">ضبط مستقیم در این مرورگر برای خروجی ogg پشتیبانی نمی‌شود؛ لطفاً فایل mp3/ogg آپلود کنید.</p>
                    )}
                    {recordPreviewUrl && (
                        <div className="mt-3">
                            <audio controls className="w-full" src={recordPreviewUrl} />
                        </div>
                    )}
                </div>

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

                        {voiceFile && !isRecording && !isStopping && (
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
                                        disabled={isSaving || isRecording || isStopping}
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
