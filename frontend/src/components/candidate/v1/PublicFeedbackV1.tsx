import React, { useEffect, useMemo, useState } from 'react';
import { CandidateData, FeedbackStatsResponse, FeedbackSubmission } from '../../../types';
import { api } from '../../../services/api';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';
import { MessageSquare, Tag, CheckCircle2, RefreshCw, Search, Trash2 } from 'lucide-react';

interface PublicFeedbackV1Props {
    candidate: CandidateData;
}

const DEFAULT_TAGS = ['اشتغال', 'مسکن', 'معیشت', 'آموزش', 'سلامت', 'سایر'] as const;

const toFaDateTime = (iso: string) => {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('fa-IR');
};

const normalizeTag = (tag: any): string | '' => {
    if (tag === null || tag === undefined) return '';
    const t = String(tag).trim();
    return t || '';
};

const isUntaggedLabel = (tag: any): boolean => {
    const t = normalizeTag(tag);
    return t === 'بدون تگ' || t === 'بدون برچسب';
};

const emptyStats = (days: 7 | 30): FeedbackStatsResponse => ({ days, total: 0, items: [] });

const PublicFeedbackV1: React.FC<PublicFeedbackV1Props> = ({ candidate }) => {
    const [items, setItems] = useState<FeedbackSubmission[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSavingId, setIsSavingId] = useState<string | null>(null);
    const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>({});
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
    const [tagFilter, setTagFilter] = useState<string>('');
    const [query, setQuery] = useState<string>('');
    const [stats7, setStats7] = useState<FeedbackStatsResponse>(() => emptyStats(7));
    const [stats30, setStats30] = useState<FeedbackStatsResponse>(() => emptyStats(30));

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    const refreshStats = async (token: string) => {
        const [s7, s30] = await Promise.all([api.getMyFeedbackStats(token, 7), api.getMyFeedbackStats(token, 30)]);
        setStats7(s7);
        setStats30(s30);
    };

    const load = async () => {
        const token = localStorage.getItem('access_token') || '';

        setIsLoading(true);
        try {
            const [data, s7, s30] = await Promise.all([
                api.getMyFeedbackSubmissions(token, 10),
                api.getMyFeedbackStats(token, 7),
                api.getMyFeedbackStats(token, 30),
            ]);
            setItems(data);
            setStats7(s7);
            setStats30(s30);
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

    // stats7/stats30 are fetched from backend to reflect the true dataset (not only the 10-item list).

    const availableTags = useMemo(() => {
        const seen = new Set<string>();
        for (const t of DEFAULT_TAGS) seen.add(t);
        for (const s of items) {
            const tag = normalizeTag(s.tag);
            if (tag) seen.add(tag);
        }
        return Array.from(seen);
    }, [items]);

    const filteredItems = useMemo(() => {
        const q = query.trim();
        return items.filter((s) => {
            const t = normalizeTag(s.tag);
            if (tagFilter && t !== tagFilter) return false;

            if (q) {
                const hay = `${s.text || ''}\n${s.answer || ''}`;
                if (!hay.includes(q)) return false;
            }

            return true;
        });
    }, [items, tagFilter, query]);

    const updateSubmission = async (id: string, patch: { tag?: string | null }) => {
        const token = localStorage.getItem('access_token') || '';

        setIsSavingId(id);
        try {
            const updated = await api.updateMyFeedbackSubmission(token, id, patch);
            setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
            // Keep the top-of-page stats accurate after tag changes.
            await refreshStats(token);
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در ذخیره', message: e?.message || 'خطا در ذخیره تغییرات' });
        } finally {
            setIsSavingId(null);
        }
    };

    const answerSubmission = async (id: string) => {
        const token = localStorage.getItem('access_token') || '';
        const answerText = (draftAnswers[id] || '').trim();

        if (!answerText) {
            setModal({ variant: 'warning', title: 'پاسخ خالی است', message: 'متن پاسخ را وارد کنید.' });
            return;
        }
        if (answerText.length > 2000) {
            setModal({ variant: 'warning', title: 'پاسخ طولانی است', message: 'متن پاسخ باید کمتر از ۲۰۰۰ کاراکتر باشد.' });
            return;
        }

        setIsSavingId(id);
        try {
            const current = items.find((x) => x.id === id);
            const currentTag = normalizeTag(current?.tag);
            // Per requirement: sending an answer should also persist the current tag.
            await api.updateMyFeedbackSubmission(token, id, { tag: currentTag ? currentTag : null });
            const updated = await api.answerMyFeedbackSubmission(token, id, answerText);
            setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
            setDraftAnswers((prev) => ({ ...prev, [id]: '' }));
            await refreshStats(token);
            setModal({ variant: 'success', title: 'ارسال شد', message: 'پاسخ ثبت شد و نوتیف در کانال/گروه ارسال می‌شود.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در ارسال پاسخ', message: e?.message || 'خطا در ارسال پاسخ' });
        } finally {
            setIsSavingId(null);
        }
    };

    const deleteSubmission = async (id: string) => {
        const token = localStorage.getItem('access_token') || '';

        setIsSavingId(id);
        try {
            await api.deleteMyFeedbackSubmission(token, id);
            setConfirmDeleteId(null);
            // Per requirement: after each deletion, refetch a fresh 10-item list and refresh stats.
            await load();
            setModal({ variant: 'success', title: 'حذف شد', message: 'پیام حذف شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در حذف', message: e?.message || 'خطا در حذف پیام' });
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

            <datalist id="feedback-tags">
                {DEFAULT_TAGS.map((t) => (
                    <option key={t} value={t} />
                ))}
            </datalist>

            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <MessageSquare size={20} className="text-blue-600" />
                        نظرات و دغدغه‌های مردمی
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
                        این بخش برای مشاهده و دسته‌بندی پیام‌هاست و می‌توانید برای هر پیام، یک پاسخ رسمی ثبت کنید.
                        بعد از ثبت پاسخ، به کانال/گروه شما نوتیف ارسال می‌شود و با کلیک، داخل بات قابل مشاهده است.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-5">
                    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                        <div className="text-sm font-bold text-gray-700 mb-2">بیشترین دغدغه‌ها در ۷ روز گذشته</div>
                        {stats7.total === 0 ? (
                            <div className="text-xs text-gray-400">موردی ثبت نشده است.</div>
                        ) : (
                            <div className="space-y-1">
                                {stats7.items.slice(0, 5).map((x) => (
                                    <div key={x.tag} className="flex items-center justify-between text-sm">
                                        <span className="text-gray-700">{x.tag}</span>
                                        <span className="text-gray-500">
                                            {isUntaggedLabel(x.tag) ? `(${x.count})` : `${x.percent}% (${x.count})`}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                        <div className="text-sm font-bold text-gray-700 mb-2">بیشترین دغدغه‌ها در ۳۰ روز گذشته</div>
                        {stats30.total === 0 ? (
                            <div className="text-xs text-gray-400">موردی ثبت نشده است.</div>
                        ) : (
                            <div className="space-y-1">
                                {stats30.items.slice(0, 5).map((x) => (
                                    <div key={x.tag} className="flex items-center justify-between text-sm">
                                        <span className="text-gray-700">{x.tag}</span>
                                        <span className="text-gray-500">
                                            {isUntaggedLabel(x.tag) ? `(${x.count})` : `${x.percent}% (${x.count})`}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <h4 className="text-sm font-bold text-gray-700">لیست پیام‌ها</h4>
                    <div className="text-xs text-gray-500">{filteredItems.length} از {items.length} پیام</div>
                </div>

                <div className="mt-4 flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
                    <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
                        <div className="flex items-center gap-2">
                            <Tag size={16} className="text-gray-400" />
                            <select
                                value={tagFilter}
                                onChange={(e) => setTagFilter(e.target.value)}
                                className="border rounded-xl px-3 py-2 bg-white text-sm w-52"
                            >
                                <option value="">همه تگ‌ها</option>
                                {availableTags.map((t) => (
                                    <option key={t} value={t}>{t}</option>
                                ))}
                            </select>
                        </div>

                        <div className="flex items-center gap-2">
                            <Search size={16} className="text-gray-400" />
                            <input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="جستجو در متن یا پاسخ..."
                                className="border rounded-xl px-3 py-2 bg-white text-sm w-64"
                            />
                        </div>
                    </div>
                </div>

                <div className="mt-4 space-y-3">
                    {filteredItems.length === 0 ? (
                        <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                            <div className="text-sm text-gray-500">هنوز پیامی ثبت نشده است.</div>
                        </div>
                    ) : (
                        filteredItems.map((s) => {
                            const currentTag = normalizeTag(s.tag);
                            const isSaving = isSavingId === s.id;
                            const normalizedStatus = String(s.status || 'NEW').toUpperCase();
                            const statusFa = normalizedStatus === 'ANSWERED' ? 'پاسخ داده شد' : (normalizedStatus === 'REVIEWED' ? 'بررسی‌شده' : 'جدید');
                            const statusClass = normalizedStatus === 'ANSWERED'
                                ? 'bg-blue-50 text-blue-700 border-blue-200'
                                : (normalizedStatus === 'REVIEWED' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-amber-50 text-amber-700 border-amber-200');
                            const hasAnswer = normalizedStatus === 'ANSWERED' || !!s.answer;
                            const answerText = String(s.answer ?? '').trim();
                            const draft = draftAnswers[s.id] ?? '';

                            return (
                                <div key={s.id} className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0 flex-1">
                                            <div className="text-sm text-gray-800 whitespace-pre-wrap break-words">{s.text}</div>

                                            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-gray-500">
                                                <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg">تاریخ: {toFaDateTime(s.created_at)}</span>
                                                {s.constituency && (
                                                    <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg">حوزه: {s.constituency}</span>
                                                )}
                                                <span className={`px-2 py-1 border rounded-lg ${statusClass}`}>وضعیت: {statusFa}</span>
                                            </div>

                                            <div className="mt-4">
                                                <div className="text-xs font-bold text-gray-700 mb-2">پاسخ رسمی</div>
                                                {hasAnswer ? (
                                                    <div className="bg-white border border-gray-200 rounded-2xl p-3 text-sm text-gray-800 whitespace-pre-wrap break-words">
                                                        {answerText || '—'}
                                                    </div>
                                                ) : (
                                                    <div className="space-y-2">
                                                        <textarea
                                                            value={draft}
                                                            onChange={(e) => setDraftAnswers((prev) => ({ ...prev, [s.id]: e.target.value }))}
                                                            placeholder="پاسخ رسمی را بنویسید..."
                                                            className="w-full border rounded-2xl px-3 py-2 bg-white text-sm min-h-[88px]"
                                                        />
                                                        <div className="flex items-center justify-end">
                                                            <button
                                                                onClick={() => void answerSubmission(s.id)}
                                                                disabled={isSaving}
                                                                className="px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                            >
                                                                {isSaving ? 'در حال ارسال...' : 'ارسال پاسخ'}
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className="w-full sm:w-auto flex sm:flex-col gap-2 items-stretch sm:items-end">
                                            <div className="flex items-center gap-2">
                                                <Tag size={16} className="text-gray-400" />
                                                <input
                                                    list="feedback-tags"
                                                    value={currentTag}
                                                    onChange={(e) => {
                                                        const nextTag = e.target.value;
                                                        setItems((prev) => prev.map((x) => (x.id === s.id ? { ...x, tag: nextTag || null } : x)));
                                                    }}
                                                    placeholder="بدون تگ"
                                                    className="border rounded-xl px-3 py-2 bg-white text-sm w-52"
                                                />
                                            </div>

                                            <div className="flex items-center gap-2 justify-end">
                                                {confirmDeleteId === s.id ? (
                                                    <>
                                                        <button
                                                            onClick={() => void deleteSubmission(s.id)}
                                                            disabled={isSaving}
                                                            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 text-white hover:bg-red-700 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                            title="حذف پیام"
                                                        >
                                                            <Trash2 size={16} />
                                                            تأیید حذف
                                                        </button>
                                                        <button
                                                            onClick={() => setConfirmDeleteId(null)}
                                                            disabled={isSaving}
                                                            className="px-4 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition disabled:bg-gray-100"
                                                        >
                                                            انصراف
                                                        </button>
                                                    </>
                                                ) : (
                                                    <button
                                                        onClick={() => setConfirmDeleteId(s.id)}
                                                        disabled={isSaving}
                                                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition disabled:bg-gray-100"
                                                        title="حذف پیام"
                                                    >
                                                        <Trash2 size={16} className="text-red-600" />
                                                        حذف
                                                    </button>
                                                )}
                                            </div>
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

export default PublicFeedbackV1;
