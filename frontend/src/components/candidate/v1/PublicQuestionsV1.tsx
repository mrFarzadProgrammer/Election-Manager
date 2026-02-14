import React, { useEffect, useMemo, useState } from 'react';
import { CandidateData, QuestionSubmission } from '../../../types';
import { api } from '../../../services/api';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';
import { HelpCircle, RefreshCw, CheckCircle2, XCircle, Lock } from 'lucide-react';

const QUESTION_CATEGORIES: string[] = [
    'اقتصاد و معیشت',
    'اشتغال',
    'مسکن',
    'شفافیت',
    'مسائل محلی حوزه انتخابیه',
];

interface PublicQuestionsV1Props {
    candidate: CandidateData;
}

const toFaDateTime = (iso: string | null | undefined) => {
    if (!iso) return '';
    const d = new Date(String(iso));
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('fa-IR');
};

const statusMeta = (status: QuestionSubmission['status']) => {
    const s = String(status || '').toUpperCase();
    if (s === 'ANSWERED') return { label: 'پاسخ داده شد', cls: 'bg-green-50 text-green-700 border-green-200' };
    if (s === 'REJECTED') return { label: 'رد شد', cls: 'bg-rose-50 text-rose-700 border-rose-200' };
    return { label: 'در انتظار', cls: 'bg-amber-50 text-amber-700 border-amber-200' };
};

const PublicQuestionsV1: React.FC<PublicQuestionsV1Props> = ({ candidate }) => {
    const [items, setItems] = useState<QuestionSubmission[]>([]);
    const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>({});
    const [draftTopics, setDraftTopics] = useState<Record<string, string>>({});
    const [draftFeatured, setDraftFeatured] = useState<Record<string, boolean>>({});
    const [isLoading, setIsLoading] = useState(false);
    const [isSavingId, setIsSavingId] = useState<string | null>(null);

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    const load = async () => {
        const token = localStorage.getItem('access_token') || '';

        setIsLoading(true);
        try {
            const data = await api.getMyQuestionSubmissions(token);
            setItems(data);
            setDraftAnswers((prev) => {
                const next: Record<string, string> = { ...prev };
                for (const q of data) {
                    if (q.id && next[q.id] === undefined) {
                        next[q.id] = '';
                    }
                }
                return next;
            });
            setDraftTopics((prev) => {
                const next: Record<string, string> = { ...prev };
                for (const q of data) {
                    if (q.id && next[q.id] === undefined) {
                        next[q.id] = String(q.topic || '');
                    }
                }
                return next;
            });
            setDraftFeatured((prev) => {
                const next: Record<string, boolean> = { ...prev };
                for (const q of data) {
                    if (q.id && next[q.id] === undefined) {
                        next[q.id] = Boolean(q.is_featured ?? false);
                    }
                }
                return next;
            });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در دریافت', message: e?.message || 'خطا در دریافت اطلاعات' });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        void load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [candidate.id]);

    const counts = useMemo(() => {
        const acc = { total: items.length, pending: 0, answered: 0, rejected: 0 };
        for (const q of items) {
            const s = String(q.status || '').toUpperCase();
            if (s === 'ANSWERED') acc.answered += 1;
            else if (s === 'REJECTED') acc.rejected += 1;
            else acc.pending += 1;
        }
        return acc;
    }, [items]);

    const answerOne = async (id: string) => {
        const token = localStorage.getItem('access_token') || '';

        const answer_text = (draftAnswers[id] || '').trim();
        if (!answer_text) {
            setModal({ variant: 'warning', title: 'پاسخ خالی', message: 'متن پاسخ را وارد کنید.' });
            return;
        }

        setIsSavingId(id);
        try {
            const topic = (draftTopics[id] || '').trim() || null;
            const is_featured = Boolean(draftFeatured[id] ?? false);
            const updated = await api.answerMyQuestionSubmission(token, id, answer_text, { topic, is_featured });
            setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در پاسخ', message: e?.message || 'خطا در ثبت پاسخ' });
        } finally {
            setIsSavingId(null);
        }
    };

    const saveMeta = async (id: string) => {
        const token = localStorage.getItem('access_token') || '';

        setIsSavingId(id);
        try {
            const topic = (draftTopics[id] || '').trim() || null;
            const is_featured = Boolean(draftFeatured[id] ?? false);
            const updated = await api.updateMyQuestionSubmissionMeta(token, id, { topic, is_featured });
            setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در ذخیره تغییرات' });
        } finally {
            setIsSavingId(null);
        }
    };

    const rejectOne = async (id: string) => {
        const token = localStorage.getItem('access_token') || '';

        setIsSavingId(id);
        try {
            const updated = await api.rejectMyQuestionSubmission(token, id);
            setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در رد', message: e?.message || 'خطا در رد سؤال' });
        } finally {
            setIsSavingId(null);
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
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <HelpCircle size={20} className="text-blue-600" />
                        سؤال‌های مردمی
                    </h3>

                    <button
                        onClick={() => void load()}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition"
                        disabled={isLoading}
                    >
                        <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
                        {isLoading ? 'در حال دریافت...' : 'به‌روزرسانی'}
                    </button>
                </div>

                <div className="mt-3 text-xs text-gray-500 leading-6">
                    <p>
                        این بخش برای دریافت سؤال‌های ساختاریافته مردم است. پس از پاسخ‌گویی، سؤال و پاسخ به‌صورت عمومی در بات منتشر می‌شود.
                        چت دوطرفه یا پاسخ فردی در این بخش وجود ندارد.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 mt-5">
                    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                        <div className="text-xs text-gray-500">کل</div>
                        <div className="text-lg font-bold text-gray-800 mt-1">{counts.total}</div>
                    </div>
                    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                        <div className="text-xs text-gray-500">در انتظار</div>
                        <div className="text-lg font-bold text-amber-700 mt-1">{counts.pending}</div>
                    </div>
                    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                        <div className="text-xs text-gray-500">پاسخ داده شد</div>
                        <div className="text-lg font-bold text-green-700 mt-1">{counts.answered}</div>
                    </div>
                    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                        <div className="text-xs text-gray-500">رد شد</div>
                        <div className="text-lg font-bold text-rose-700 mt-1">{counts.rejected}</div>
                    </div>
                </div>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <h4 className="text-sm font-bold text-gray-700">لیست سؤال‌ها</h4>
                    <div className="text-xs text-gray-500">{items.length} مورد</div>
                </div>

                <div className="mt-4 space-y-3">
                    {items.length === 0 ? (
                        <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                            <div className="text-sm text-gray-500">هنوز سؤالی ثبت نشده است.</div>
                        </div>
                    ) : (
                        items.map((q) => {
                            const meta = statusMeta(q.status);
                            const isSaving = isSavingId === q.id;
                            const isAnswered = String(q.status).toUpperCase() === 'ANSWERED';
                            const isRejected = String(q.status).toUpperCase() === 'REJECTED';
                            const topicValue = draftTopics[q.id] ?? String(q.topic || '');
                            const featuredValue = Boolean(draftFeatured[q.id] ?? q.is_featured ?? false);

                            return (
                                <div key={q.id} className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                                    <div className="flex items-start justify-between gap-3 flex-wrap">
                                        <div className="min-w-0 flex-1">
                                            <div className="text-sm text-gray-800 whitespace-pre-wrap break-words">{q.text}</div>

                                            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-gray-500">
                                                <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg">تاریخ: {toFaDateTime(q.created_at)}</span>
                                                {q.constituency && (
                                                    <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg">حوزه: {q.constituency}</span>
                                                )}
                                                {q.topic && (
                                                    <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg">موضوع: {q.topic}</span>
                                                )}
                                                <span className={`px-2 py-1 border rounded-lg ${meta.cls}`}>وضعیت: {meta.label}</span>
                                                {isAnswered && q.answered_at && (
                                                    <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg">پاسخ در: {toFaDateTime(q.answered_at)}</span>
                                                )}
                                            </div>

                                            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2">
                                                <div className="sm:col-span-2">
                                                    <label className="block text-xs font-bold text-gray-600 mb-2">دسته‌بندی</label>
                                                    <select
                                                        value={topicValue}
                                                        onChange={(e) => setDraftTopics((prev) => ({ ...prev, [q.id]: e.target.value }))}
                                                        className="w-full border border-gray-200 rounded-2xl px-3 py-2 bg-white text-sm"
                                                        disabled={isSaving}
                                                    >
                                                        <option value="">(بدون دسته‌بندی)</option>
                                                        {QUESTION_CATEGORIES.map((c) => (
                                                            <option key={c} value={c}>
                                                                {c}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>

                                                <div className="flex flex-col justify-end">
                                                    <label className="block text-xs font-bold text-gray-600 mb-2">منتخب</label>
                                                    <button
                                                        type="button"
                                                        onClick={() => setDraftFeatured((prev) => ({ ...prev, [q.id]: !featuredValue }))}
                                                        disabled={isSaving}
                                                        className={`w-full px-3 py-2 rounded-2xl border text-sm transition ${featuredValue
                                                            ? 'bg-green-50 border-green-200 text-green-700'
                                                            : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                                                            }`}
                                                        title="سؤال‌های منتخب در بخش پرتکرار بات نمایش داده می‌شوند"
                                                    >
                                                        {featuredValue ? 'منتخب است' : 'منتخب نیست'}
                                                    </button>
                                                </div>
                                            </div>

                                            {isAnswered && (
                                                <div className="mt-4 bg-white border border-gray-200 rounded-2xl p-3">
                                                    <div className="text-xs font-bold text-gray-600 mb-2">پاسخ رسمی (Immutable)</div>
                                                    <div className="text-sm text-gray-800 whitespace-pre-wrap break-words">{q.answer_text || '—'}</div>
                                                </div>
                                            )}

                                            {!isAnswered && !isRejected && (
                                                <div className="mt-4">
                                                    <label className="block text-xs font-bold text-gray-600 mb-2">پاسخ نماینده</label>
                                                    <textarea
                                                        value={draftAnswers[q.id] ?? ''}
                                                        onChange={(e) => setDraftAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                                                        placeholder="پاسخ را وارد کنید..."
                                                        className="w-full min-h-[96px] border border-gray-200 rounded-2xl p-3 bg-white text-sm"
                                                    />
                                                    <div className="mt-2 text-[11px] text-gray-400">با ثبت پاسخ، این سؤال به‌صورت عمومی در بات نمایش داده می‌شود.</div>
                                                </div>
                                            )}

                                            {isRejected && (
                                                <div className="mt-4 text-xs text-gray-500 inline-flex items-center gap-2">
                                                    <Lock size={14} className="text-gray-400" />
                                                    این سؤال رد شده و در بات نمایش داده نمی‌شود.
                                                </div>
                                            )}
                                        </div>

                                        <div className="w-full sm:w-auto flex flex-row sm:flex-col gap-2 items-stretch sm:items-end">
                                            {!isAnswered && !isRejected ? (
                                                <>
                                                    <button
                                                        onClick={() => void answerOne(q.id)}
                                                        disabled={isSaving}
                                                        className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-green-600 text-white hover:bg-green-700 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                    >
                                                        <CheckCircle2 size={16} />
                                                        {isSaving ? 'در حال ثبت...' : 'ثبت پاسخ'}
                                                    </button>
                                                    <button
                                                        onClick={() => void rejectOne(q.id)}
                                                        disabled={isSaving}
                                                        className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                        title="بدون ارسال پیام به کاربر"
                                                    >
                                                        <XCircle size={16} />
                                                        رد
                                                    </button>
                                                </>
                                            ) : (
                                                <button
                                                    onClick={() => void saveMeta(q.id)}
                                                    disabled={isSaving}
                                                    className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gray-800 text-white hover:bg-gray-900 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                    title="پاسخ رسمی تغییر نمی‌کند؛ فقط دسته‌بندی/منتخب بودن ذخیره می‌شود"
                                                >
                                                    <Lock size={16} />
                                                    {isSaving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
};

export default PublicQuestionsV1;
