import React, { useEffect, useMemo, useState } from 'react';
import { CandidateData, FeedbackSubmission } from '../../../types';
import { api } from '../../../services/api';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';
import { MessageSquare, Tag, CheckCircle2, RefreshCw } from 'lucide-react';

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

const withinDays = (createdAtIso: string, days: 7 | 30) => {
    const d = new Date(createdAtIso);
    if (Number.isNaN(d.getTime())) return false;
    const ms = days * 24 * 60 * 60 * 1000;
    return Date.now() - d.getTime() <= ms;
};

const computeTagStats = (items: FeedbackSubmission[], days: 7 | 30) => {
    const filtered = items.filter((x) => withinDays(x.created_at, days));
    const total = filtered.length;
    const counts: Record<string, number> = {};

    for (const s of filtered) {
        const t = normalizeTag(s.tag) || 'سایر';
        counts[t] = (counts[t] || 0) + 1;
    }

    const sorted = Object.entries(counts)
        .map(([tag, count]) => ({ tag, count, percent: total ? Math.round((count / total) * 100) : 0 }))
        .sort((a, b) => b.count - a.count);

    return { total, items: sorted };
};

const PublicFeedbackV1: React.FC<PublicFeedbackV1Props> = ({ candidate }) => {
    const [items, setItems] = useState<FeedbackSubmission[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSavingId, setIsSavingId] = useState<string | null>(null);

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    const load = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }

        setIsLoading(true);
        try {
            const data = await api.getMyFeedbackSubmissions(token);
            setItems(data);
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

    const stats7 = useMemo(() => computeTagStats(items, 7), [items]);
    const stats30 = useMemo(() => computeTagStats(items, 30), [items]);

    const updateSubmission = async (id: string, patch: { tag?: string | null; status?: 'NEW' | 'REVIEWED' }) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }

        setIsSavingId(id);
        try {
            const updated = await api.updateMyFeedbackSubmission(token, id, patch);
            setItems((prev) => prev.map((x) => (x.id === id ? updated : x)));
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا در ذخیره', message: e?.message || 'خطا در ذخیره تغییرات' });
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
                        این بخش فقط برای مشاهده، تحلیل و گزارش دغدغه‌های پرتکرار است و پاسخ فردی ندارد.
                        پاسخ رسمی فقط از طریق «❓ سؤال از نماینده» یا جمع‌بندی‌های عمومی ارائه می‌شود.
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
                                        <span className="text-gray-500">{x.percent}% ({x.count})</span>
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
                                        <span className="text-gray-500">{x.percent}% ({x.count})</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <h4 className="text-sm font-bold text-gray-700">لیست پیام‌ها (Read-only)</h4>
                    <div className="text-xs text-gray-500">{items.length} پیام</div>
                </div>

                <div className="mt-4 space-y-3">
                    {items.length === 0 ? (
                        <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                            <div className="text-sm text-gray-500">هنوز پیامی ثبت نشده است.</div>
                        </div>
                    ) : (
                        items.map((s) => {
                            const currentTag = normalizeTag(s.tag);
                            const isSaving = isSavingId === s.id;
                            const statusFa = s.status === 'REVIEWED' ? 'بررسی‌شده' : 'جدید';
                            const statusClass = s.status === 'REVIEWED' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-amber-50 text-amber-700 border-amber-200';

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
                                                <button
                                                    onClick={() => void updateSubmission(s.id, { tag: currentTag ? currentTag : null })}
                                                    disabled={isSaving}
                                                    className="px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                >
                                                    {isSaving ? 'در حال ذخیره...' : 'ذخیره تگ'}
                                                </button>
                                                {s.status !== 'REVIEWED' && (
                                                    <button
                                                        onClick={() => void updateSubmission(s.id, { status: 'REVIEWED' })}
                                                        disabled={isSaving}
                                                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-green-600 text-white hover:bg-green-700 transition disabled:bg-gray-300 disabled:text-gray-700"
                                                        title="بدون ارسال پیام به کاربر؛ فقط برای مدیریت داخلی"
                                                    >
                                                        <CheckCircle2 size={16} />
                                                        بررسی شد
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
