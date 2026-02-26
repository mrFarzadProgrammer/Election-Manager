import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Save, ListChecks } from 'lucide-react';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface FixedProgramsV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

type FixedProgramQuestion = {
    tag: string;
    prompt: string;
    note?: string;
};

const QUESTIONS: FixedProgramQuestion[] = [
    {
        tag: 'شفافیت و فساد',
        prompt: 'برنامه عملی شما برای شفاف‌سازی تصمیمات شورای شهر و مقابله با رانت دقیقاً چیه؟',
        note: 'نه شعار؛ ابزار، سامانه یا مکانیزم مشخص',
    },
    {
        tag: 'ترافیک و حمل‌ونقل',
        prompt: 'برای کاهش ترافیک روزمره تهران، چه اقدام کوتاه‌مدت و چه اصلاح بلندمدتی در نظر دارید؟',
    },
    {
        tag: 'مسکن و اجاره',
        prompt: 'شورای شهر چه نقشی می‌تونه در کنترل اجاره‌بها و ساماندهی بازار مسکن داشته باشه و برنامه شما چیه؟',
    },
    {
        tag: 'کیفیت زندگی محله‌ای',
        prompt: 'اگر اختیار داشتید فقط روی «یک تغییر محله‌ای» تمرکز کنید که سریع حس بشه، اون چیه؟',
    },
    {
        tag: 'آلودگی هوا',
        prompt: 'برنامه مشخص شما برای کاهش آلودگی هوا چیه و چه بخشی از اون در اختیار شوراست؟',
    },
    {
        tag: 'عدالت شهری',
        prompt: 'چطور می‌خواید فاصله خدمات شهری بین شمال و جنوب تهران رو کمتر کنید؟',
    },
    {
        tag: 'مدیریت شهری هوشمند',
        prompt: 'آیا برنامه‌ای برای استفاده از داده، هوش مصنوعی یا شهر هوشمند در تصمیمات شهری دارید؟ کجا دقیقاً؟',
    },
    {
        tag: 'مشارکت مردم',
        prompt: 'مردم چطور می‌تونن بعد از انتخاب شما، در تصمیمات شهری نظر بدن و اثر واقعی بذارن؟',
    },
    {
        tag: 'پاسخگویی نمایندگان',
        prompt: 'اگر یک تصمیم شما با اعتراض مردم مواجه شد، سازوکار پاسخگویی‌تون چیه؟',
    },
    {
        tag: 'ارتباط مستمر',
        prompt: 'آیا متعهد می‌شید بعد از انتخابات، همین مسیر ارتباطی با مردم حفظ بشه و گزارش‌های منظم، شفاف و غیرتبلیغاتی ارائه بدید؟',
        note: 'خیلی مهم',
    },
];

const MAX_ANSWER = 600;
const QUESTION_COUNT = 10;

const readPrograms = (candidate: CandidateData): string[] => {
    const botConfig = candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {};
    const programs = (botConfig as any).programs;
    if (Array.isArray(programs)) {
        const arr = programs.map((x) => String(x || '').trim());
        while (arr.length < QUESTION_COUNT) arr.push('');
        return arr.slice(0, QUESTION_COUNT);
    }
    return Array.from({ length: QUESTION_COUNT }, () => '');
};

const FixedProgramsV1: React.FC<FixedProgramsV1Props> = ({ candidate, onUpdate }) => {
    const initial = useMemo(() => readPrograms(candidate), [candidate]);
    const [answers, setAnswers] = useState<string[]>(initial);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);
    const [introOpen, setIntroOpen] = useState(true);
    const lastCandidateIdRef = useRef<string>(candidate.id);

    useEffect(() => {
        const candidateChanged = lastCandidateIdRef.current !== candidate.id;
        if (candidateChanged) {
            lastCandidateIdRef.current = candidate.id;
            setIsDirty(false);
        }

        if (!isDirty || candidateChanged) {
            setAnswers(readPrograms(candidate));
        }
    }, [candidate, isDirty]);

    const setAnswer = (idx: number, value: string) => {
        setIsDirty(true);
        setAnswers((prev) => prev.map((p, i) => (i === idx ? value : p)));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const normalized = answers.map((a) => String(a || '').trim()).slice(0, QUESTION_COUNT);
            while (normalized.length < QUESTION_COUNT) normalized.push('');

            const bot_config = {
                ...(candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}),
                programs: normalized,
            };

            await onUpdate({ bot_config });
            setIsDirty(false);
            setModal({ variant: 'success', title: 'ذخیره شد', message: 'تغییرات با موفقیت ذخیره شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در ذخیره', message: e?.message || 'خطا در ذخیره' });
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <ResultModal
                open={introOpen}
                variant="info"
                title="نکته مهم"
                message="این پرسش‌ها به‌صورت یکسان از همه کاندیداها پرسیده می‌شود تا مردم بتوانند دیدگاه‌ها و برنامه‌های نامزدهای مختلف را درباره مسائل مشترک شهری، شفاف و قابل مقایسه ببینند."
                primaryLabel="متوجه شدم"
                dismissable={false}
                onClose={() => setIntroOpen(false)}
            />
            <ResultModal
                open={!!modal}
                variant={modal?.variant || 'info'}
                title={modal?.title || ''}
                message={modal?.message || ''}
                onClose={() => setModal(null)}
            />
            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <ListChecks size={20} className="text-blue-600" />
                    برنامه‌ها (۱۰ سؤال ثابت)
                </h3>

                <div className="space-y-4">
                    {QUESTIONS.map((q, idx) => (
                        <div key={idx} className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                            <div className="flex items-center justify-between gap-3">
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100 text-[11px] font-bold">
                                            {q.tag}
                                        </span>
                                        {q.note && (
                                            <span className="text-[11px] text-gray-500">({q.note})</span>
                                        )}
                                    </div>
                                    <p className="text-sm font-bold text-gray-700 mt-2 leading-6">
                                        {idx + 1}) {q.prompt}
                                    </p>
                                </div>
                                <span className={`text-xs ${answers[idx]?.length > MAX_ANSWER ? 'text-red-600' : 'text-gray-400'}`}>{(answers[idx] || '').length}/{MAX_ANSWER}</span>
                            </div>
                            <textarea
                                value={answers[idx] || ''}
                                maxLength={MAX_ANSWER}
                                onChange={(e) => setAnswer(idx, e.target.value)}
                                className="w-full mt-3 p-4 bg-white border border-gray-200 rounded-xl text-right text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none h-28"
                                placeholder="پاسخ خود را بنویسید..."
                            />
                        </div>
                    ))}
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

export default FixedProgramsV1;
