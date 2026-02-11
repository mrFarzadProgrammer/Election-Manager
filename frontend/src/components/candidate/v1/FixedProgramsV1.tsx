import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Save, ListChecks } from 'lucide-react';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface FixedProgramsV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

const QUESTIONS = [
    '1) اولویت اول شما در مجلس برای این حوزه چیست؟',
    '2) مهم‌ترین مشکل فعلی مردم این حوزه از نگاه شما چیست؟',
    '3) برای اشتغال و اقتصاد منطقه چه برنامه‌ای دارید؟',
    '4) درباره شفافیت، پاسخگویی و گزارش‌دهی به مردم چه تعهدی می‌دهید؟',
    '5) برنامه شما برای پیگیری مطالبات محلی (زیرساخت، بهداشت، آموزش) چیست؟',
];

const MAX_ANSWER = 600;

const readPrograms = (candidate: CandidateData): string[] => {
    const botConfig = candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {};
    const programs = (botConfig as any).programs;
    if (Array.isArray(programs)) {
        const arr = programs.map((x) => String(x || '').trim());
        while (arr.length < 5) arr.push('');
        return arr.slice(0, 5);
    }
    return Array.from({ length: 5 }, () => '');
};

const FixedProgramsV1: React.FC<FixedProgramsV1Props> = ({ candidate, onUpdate }) => {
    const initial = useMemo(() => readPrograms(candidate), [candidate]);
    const [answers, setAnswers] = useState<string[]>(initial);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);
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
            const normalized = answers.map((a) => String(a || '').trim()).slice(0, 5);
            while (normalized.length < 5) normalized.push('');

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
                open={!!modal}
                variant={modal?.variant || 'info'}
                title={modal?.title || ''}
                message={modal?.message || ''}
                onClose={() => setModal(null)}
            />
            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <ListChecks size={20} className="text-blue-600" />
                    برنامه‌ها (۵ سؤال ثابت)
                </h3>

                <div className="space-y-4">
                    {QUESTIONS.map((q, idx) => (
                        <div key={idx} className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                            <div className="flex items-center justify-between gap-3">
                                <p className="text-sm font-bold text-gray-700">{q}</p>
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
