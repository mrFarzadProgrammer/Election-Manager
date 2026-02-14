import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import {
    BehaviorCounterItem,
    CommitmentLearningItem,
    FlowPathItem,
    GlobalBotUserItem,
    LeadItem,
    MvpOverviewResponse,
    QuestionLearningItem,
    UxLogItem,
} from '../../types';

type CandidateOption = { id: number; name: string };

type LoadState<T> =
    | { status: 'idle' | 'loading'; data: T | null; error: string | null }
    | { status: 'ready'; data: T; error: string | null };

const formatDateTime = (value?: string | null) => {
    if (!value) return '';
    // Backend returns ISO; keep it simple and readable.
    return String(value).replace('T', ' ').replace('Z', '');
};

const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
};

const MvpLearningTab: React.FC = () => {
    const token = localStorage.getItem('access_token') || '';

    const [overview, setOverview] = useState<LoadState<MvpOverviewResponse>>({ status: 'loading', data: null, error: null });

    const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);

    const [behavior, setBehavior] = useState<LoadState<BehaviorCounterItem[]>>({ status: 'idle', data: null, error: null });
    const [paths, setPaths] = useState<LoadState<FlowPathItem[]>>({ status: 'idle', data: null, error: null });

    const [questionStatus, setQuestionStatus] = useState<string>('');
    const [questions, setQuestions] = useState<LoadState<QuestionLearningItem[]>>({ status: 'idle', data: null, error: null });
    const [commitments, setCommitments] = useState<LoadState<CommitmentLearningItem[]>>({ status: 'idle', data: null, error: null });
    const [leads, setLeads] = useState<LoadState<LeadItem[]>>({ status: 'idle', data: null, error: null });

    const [uxAction, setUxAction] = useState<string>('');
    const [uxLogs, setUxLogs] = useState<LoadState<UxLogItem[]>>({ status: 'idle', data: null, error: null });

    // Global users (Super Admin only, backend enforced)
    const [globalRepresentativeId, setGlobalRepresentativeId] = useState<number | null>(null);
    const [globalStartDate, setGlobalStartDate] = useState<string>('');
    const [globalEndDate, setGlobalEndDate] = useState<string>('');
    const [globalInteractionType, setGlobalInteractionType] = useState<'' | 'question' | 'comment' | 'lead'>('');
    const [globalUsers, setGlobalUsers] = useState<LoadState<GlobalBotUserItem[]>>({ status: 'idle', data: null, error: null });
    const [isExporting, setIsExporting] = useState(false);

    const candidates: CandidateOption[] = useMemo(() => {
        const items = overview.data?.per_candidate || [];
        return items
            .map((c) => ({ id: c.candidate_id, name: c.name || `نماینده ${c.candidate_id}` }))
            .sort((a, b) => a.id - b.id);
    }, [overview.data]);

    const effectiveCandidateId = selectedCandidateId;

    useEffect(() => {
        let mounted = true;
        (async () => {
            try {
                setOverview({ status: 'loading', data: null, error: null });
                const data = await api.getAdminMvpOverview(token);
                if (!mounted) return;
                setOverview({ status: 'ready', data, error: null });
            } catch (e: any) {
                if (!mounted) return;
                setOverview({ status: 'idle', data: null, error: e?.message || 'خطا در دریافت اطلاعات' });
            }
        })();
        return () => {
            mounted = false;
        };
    }, [token]);

    const loadBehaviorAndPaths = async () => {
        try {
            setBehavior({ status: 'loading', data: null, error: null });
            setPaths({ status: 'loading', data: null, error: null });

            const [b, p] = await Promise.all([
                api.getAdminMvpBehavior(token, effectiveCandidateId),
                api.getAdminMvpPaths(token, { candidateId: effectiveCandidateId, limit: 3 }),
            ]);

            setBehavior({ status: 'ready', data: b.items || [], error: null });
            setPaths({ status: 'ready', data: p.items || [], error: null });
        } catch (e: any) {
            setBehavior({ status: 'idle', data: null, error: e?.message || 'خطا در دریافت آمار رفتار' });
            setPaths({ status: 'idle', data: null, error: e?.message || 'خطا در دریافت مسیرها' });
        }
    };

    const loadLearningLists = async () => {
        try {
            setQuestions({ status: 'loading', data: null, error: null });
            setCommitments({ status: 'loading', data: null, error: null });
            setLeads({ status: 'loading', data: null, error: null });

            const [q, c, l] = await Promise.all([
                api.getAdminMvpQuestions(token, { candidateId: effectiveCandidateId, status: questionStatus || null }),
                api.getAdminMvpCommitments(token, effectiveCandidateId),
                api.getAdminMvpLeads(token, effectiveCandidateId),
            ]);

            setQuestions({ status: 'ready', data: q || [], error: null });
            setCommitments({ status: 'ready', data: c || [], error: null });
            setLeads({ status: 'ready', data: l || [], error: null });
        } catch (e: any) {
            const msg = e?.message || 'خطا در دریافت لیست‌ها';
            setQuestions({ status: 'idle', data: null, error: msg });
            setCommitments({ status: 'idle', data: null, error: msg });
            setLeads({ status: 'idle', data: null, error: msg });
        }
    };

    const loadUxLogs = async () => {
        try {
            setUxLogs({ status: 'loading', data: null, error: null });
            const logs = await api.getAdminMvpUxLogs(token, {
                candidateId: effectiveCandidateId,
                action: uxAction || null,
                limit: 200,
            });
            setUxLogs({ status: 'ready', data: logs || [], error: null });
        } catch (e: any) {
            setUxLogs({ status: 'idle', data: null, error: e?.message || 'خطا در دریافت لاگ‌ها' });
        }
    };

    const loadGlobalUsers = async () => {
        try {
            setGlobalUsers({ status: 'loading', data: null, error: null });
            const rows = await api.getAdminMvpGlobalUsers(token, {
                representativeId: globalRepresentativeId,
                startDate: globalStartDate ? `${globalStartDate}T00:00:00` : null,
                endDate: globalEndDate ? `${globalEndDate}T23:59:59` : null,
                interactionType: globalInteractionType || null,
                limit: 1000,
            });
            setGlobalUsers({ status: 'ready', data: rows || [], error: null });
        } catch (e: any) {
            setGlobalUsers({ status: 'idle', data: null, error: e?.message || 'خطا در دریافت کاربران' });
        }
    };

    const exportGlobalUsers = async () => {
        try {
            setIsExporting(true);
            const blob = await api.exportAdminMvpGlobalUsersXlsx(token, {
                representativeId: globalRepresentativeId,
                startDate: globalStartDate ? `${globalStartDate}T00:00:00` : null,
                endDate: globalEndDate ? `${globalEndDate}T23:59:59` : null,
                interactionType: globalInteractionType || null,
            });
            const ts = new Date();
            const filename = `global_users_${ts.getFullYear()}-${String(ts.getMonth() + 1).padStart(2, '0')}-${String(ts.getDate()).padStart(2, '0')}.xlsx`;
            downloadBlob(blob, filename);
        } catch (e: any) {
            alert(e?.message || 'خطا در خروجی اکسل');
        } finally {
            setIsExporting(false);
        }
    };

    const globalCounters = overview.data?.global_counters;

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                    <h2 className="text-xl font-bold text-gray-800">پنل یادگیری (MVP)</h2>
                    <p className="text-sm text-gray-500">فقط خواندنی — برای مشاهده رفتار و داده‌های بات</p>
                </div>
                <div className="flex items-center gap-2">
                    <label className="text-sm text-gray-600">نماینده:</label>
                    <select
                        className="border rounded-xl px-3 py-2 bg-white"
                        value={selectedCandidateId == null ? '' : String(selectedCandidateId)}
                        onChange={(e) => setSelectedCandidateId(e.target.value ? Number(e.target.value) : null)}
                    >
                        <option value="">کل سیستم</option>
                        {candidates.map((c) => (
                            <option key={c.id} value={String(c.id)}>
                                {c.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-4">
                <div className="flex items-center justify-between gap-3">
                    <h3 className="font-bold text-gray-800">نمای کلی</h3>
                    <button
                        className="px-3 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm"
                        onClick={() => {
                            // refresh overview
                            setOverview({ status: 'loading', data: null, error: null });
                            api.getAdminMvpOverview(token)
                                .then((data) => setOverview({ status: 'ready', data, error: null }))
                                .catch((e: any) => setOverview({ status: 'idle', data: null, error: e?.message || 'خطا' }));
                        }}
                    >
                        بروزرسانی
                    </button>
                </div>

                {overview.status === 'loading' && <div className="mt-3 text-sm text-gray-500">در حال بارگذاری...</div>}
                {overview.error && <div className="mt-3 text-sm text-red-600">{overview.error}</div>}

                {globalCounters && (
                    <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500">کل کاربران</div><div className="text-lg font-bold">{globalCounters.total_users}</div></div>
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500" title="کاربرانی که حداقل یک تعامل در ۷ روز گذشته داشته‌اند">کاربران فعال (۷ روز)</div><div className="text-lg font-bold">{globalCounters.active_users}</div></div>
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500">سوال‌ها</div><div className="text-lg font-bold">{globalCounters.total_questions}</div></div>
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500">پاسخ داده شده</div><div className="text-lg font-bold">{globalCounters.answered_questions}</div></div>
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500">نظرها</div><div className="text-lg font-bold">{globalCounters.total_comments}</div></div>
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500">تعهدات</div><div className="text-lg font-bold">{globalCounters.total_commitments}</div></div>
                        <div className="bg-gray-50 rounded-xl p-3 border"><div className="text-xs text-gray-500">سرنخ‌ها</div><div className="text-lg font-bold">{globalCounters.total_leads}</div></div>
                    </div>
                )}

                {overview.data?.per_candidate?.length ? (
                    <div className="mt-5 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-right text-gray-500">
                                    <th className="py-2 px-3">نماینده</th>
                                    <th className="py-2 px-3">کاربران</th>
                                    <th className="py-2 px-3" title="کاربرانی که حداقل یک تعامل در ۷ روز گذشته داشته‌اند">فعال (۷ روز)</th>
                                    <th className="py-2 px-3">سوال</th>
                                    <th className="py-2 px-3">پاسخ</th>
                                    <th className="py-2 px-3">نظر</th>
                                    <th className="py-2 px-3">تعهد</th>
                                    <th className="py-2 px-3">سرنخ</th>
                                </tr>
                            </thead>
                            <tbody>
                                {overview.data.per_candidate.map((c) => (
                                    <tr key={c.candidate_id} className="border-t">
                                        <td className="py-2 px-3 font-medium text-gray-800">{c.name || `نماینده ${c.candidate_id}`}</td>
                                        <td className="py-2 px-3">{c.counters.total_users}</td>
                                        <td className="py-2 px-3">{c.counters.active_users}</td>
                                        <td className="py-2 px-3">{c.counters.total_questions}</td>
                                        <td className="py-2 px-3">{c.counters.answered_questions}</td>
                                        <td className="py-2 px-3">{c.counters.total_comments}</td>
                                        <td className="py-2 px-3">{c.counters.total_commitments}</td>
                                        <td className="py-2 px-3">{c.counters.total_leads}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : null}
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <h3 className="font-bold text-gray-800">رفتار و مسیرها</h3>
                    <button
                        className="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm"
                        onClick={loadBehaviorAndPaths}
                    >
                        بروزرسانی
                    </button>
                </div>

                {(behavior.status === 'loading' || paths.status === 'loading') && <div className="mt-3 text-sm text-gray-500">در حال بارگذاری...</div>}
                {(behavior.error || paths.error) && <div className="mt-3 text-sm text-red-600">{behavior.error || paths.error}</div>}

                <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="border rounded-2xl p-3">
                        <div className="font-semibold text-gray-800 mb-2">شمارنده رویدادها</div>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="text-right text-gray-500">
                                        <th className="py-2 px-3">رویداد</th>
                                        <th className="py-2 px-3">تعداد</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(behavior.data || []).map((it) => (
                                        <tr key={it.event} className="border-t">
                                            <td className="py-2 px-3">{it.event}</td>
                                            <td className="py-2 px-3 font-medium">{it.count}</td>
                                        </tr>
                                    ))}
                                    {!behavior.data?.length && behavior.status === 'ready' && (
                                        <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={2}>داده‌ای ثبت نشده</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="border rounded-2xl p-3">
                        <div className="font-semibold text-gray-800 mb-2">Top مسیرهای کاربر</div>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="text-right text-gray-500">
                                        <th className="py-2 px-3">مسیر</th>
                                        <th className="py-2 px-3">تعداد</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(paths.data || []).map((it, idx) => (
                                        <tr key={`${it.path}-${idx}`} className="border-t">
                                            <td className="py-2 px-3 font-mono text-xs" dir="ltr">{it.path}</td>
                                            <td className="py-2 px-3 font-medium">{it.count}</td>
                                        </tr>
                                    ))}
                                    {!paths.data?.length && paths.status === 'ready' && (
                                        <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={2}>داده‌ای ثبت نشده</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                    <h3 className="font-bold text-gray-800">یادگیری (سوال‌ها / تعهدات / سرنخ‌ها)</h3>
                    <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
                        <select
                            className="border rounded-xl px-3 py-2 bg-white"
                            value={questionStatus}
                            onChange={(e) => setQuestionStatus(e.target.value)}
                        >
                            <option value="">همه وضعیت‌ها</option>
                            <option value="NEW">جدید</option>
                            <option value="ANSWERED">پاسخ داده شده</option>
                            <option value="PUBLISHED">منتشر شده</option>
                        </select>
                        <button
                            className="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm"
                            onClick={loadLearningLists}
                        >
                            بروزرسانی
                        </button>
                    </div>
                </div>

                {(questions.status === 'loading' || commitments.status === 'loading' || leads.status === 'loading') && (
                    <div className="mt-3 text-sm text-gray-500">در حال بارگذاری...</div>
                )}
                {(questions.error || commitments.error || leads.error) && (
                    <div className="mt-3 text-sm text-red-600">{questions.error || commitments.error || leads.error}</div>
                )}

                <div className="mt-4 space-y-6">
                    <div className="overflow-x-auto">
                        <div className="font-semibold text-gray-800 mb-2">سوال‌ها</div>
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-right text-gray-500">
                                    <th className="py-2 px-3">ID</th>
                                    <th className="py-2 px-3">کاربر</th>
                                    <th className="py-2 px-3">دسته</th>
                                    <th className="py-2 px-3">وضعیت</th>
                                    <th className="py-2 px-3">ایجاد</th>
                                    <th className="py-2 px-3">پاسخ</th>
                                    <th className="py-2 px-3">بازدید</th>
                                    <th className="py-2 px-3">کلیک کانال</th>
                                    <th className="py-2 px-3">متن</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(questions.data || []).map((q) => (
                                    <tr key={q.question_id} className="border-t">
                                        <td className="py-2 px-3 font-medium">{q.question_id}</td>
                                        <td className="py-2 px-3" dir="ltr">{q.user_id}</td>
                                        <td className="py-2 px-3">{q.category || '-'}</td>
                                        <td className="py-2 px-3">{q.status}</td>
                                        <td className="py-2 px-3" dir="ltr">{formatDateTime(q.created_at)}</td>
                                        <td className="py-2 px-3" dir="ltr">{formatDateTime(q.answered_at)}</td>
                                        <td className="py-2 px-3">{q.answer_views_count}</td>
                                        <td className="py-2 px-3">{q.channel_click_count}</td>
                                        <td className="py-2 px-3 max-w-[380px] truncate">{q.question_text}</td>
                                    </tr>
                                ))}
                                {!questions.data?.length && questions.status === 'ready' && (
                                    <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={9}>موردی یافت نشد</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="overflow-x-auto border rounded-2xl p-3">
                            <div className="font-semibold text-gray-800 mb-2">تعهدات</div>
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="text-right text-gray-500">
                                        <th className="py-2 px-3">ID</th>
                                        <th className="py-2 px-3">عنوان</th>
                                        <th className="py-2 px-3">ایجاد</th>
                                        <th className="py-2 px-3">بازدید</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(commitments.data || []).map((c) => (
                                        <tr key={c.commitment_id} className="border-t">
                                            <td className="py-2 px-3 font-medium">{c.commitment_id}</td>
                                            <td className="py-2 px-3 max-w-[260px] truncate">{c.title}</td>
                                            <td className="py-2 px-3" dir="ltr">{formatDateTime(c.created_at)}</td>
                                            <td className="py-2 px-3">{c.view_count}</td>
                                        </tr>
                                    ))}
                                    {!commitments.data?.length && commitments.status === 'ready' && (
                                        <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={4}>موردی یافت نشد</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>

                        <div className="overflow-x-auto border rounded-2xl p-3">
                            <div className="font-semibold text-gray-800 mb-2">سرنخ‌ها (Build bot)</div>
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="text-right text-gray-500">
                                        <th className="py-2 px-3">ID</th>
                                        <th className="py-2 px-3">ایجاد</th>
                                        <th className="py-2 px-3">کاربر</th>
                                        <th className="py-2 px-3">نقش</th>
                                        <th className="py-2 px-3">تلفن</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(leads.data || []).map((l) => (
                                        <tr key={l.lead_id} className="border-t">
                                            <td className="py-2 px-3 font-medium">{l.lead_id}</td>
                                            <td className="py-2 px-3" dir="ltr">{formatDateTime(l.created_at)}</td>
                                            <td className="py-2 px-3" dir="ltr">{l.user_id}</td>
                                            <td className="py-2 px-3">{l.selected_role || '-'}</td>
                                            <td className="py-2 px-3" dir="ltr">{l.phone || '-'}</td>
                                        </tr>
                                    ))}
                                    {!leads.data?.length && leads.status === 'ready' && (
                                        <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={5}>موردی یافت نشد</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                    <h3 className="font-bold text-gray-800">لاگ UX (خطا/رهاکردن مسیر)</h3>
                    <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
                        <input
                            className="border rounded-xl px-3 py-2 bg-white"
                            placeholder="فیلتر action (اختیاری)"
                            value={uxAction}
                            onChange={(e) => setUxAction(e.target.value)}
                        />
                        <button
                            className="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm"
                            onClick={loadUxLogs}
                        >
                            بروزرسانی
                        </button>
                    </div>
                </div>

                {uxLogs.status === 'loading' && <div className="mt-3 text-sm text-gray-500">در حال بارگذاری...</div>}
                {uxLogs.error && <div className="mt-3 text-sm text-red-600">{uxLogs.error}</div>}

                <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="text-right text-gray-500">
                                <th className="py-2 px-3">ID</th>
                                <th className="py-2 px-3">زمان</th>
                                <th className="py-2 px-3">کاربر</th>
                                <th className="py-2 px-3">state</th>
                                <th className="py-2 px-3">action</th>
                                <th className="py-2 px-3">expected_action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(uxLogs.data || []).map((r) => (
                                <tr key={r.id} className="border-t">
                                    <td className="py-2 px-3 font-medium">{r.id}</td>
                                    <td className="py-2 px-3" dir="ltr">{formatDateTime(r.timestamp)}</td>
                                    <td className="py-2 px-3" dir="ltr">{r.user_id}</td>
                                    <td className="py-2 px-3">{r.state || '-'}</td>
                                    <td className="py-2 px-3">{r.action}</td>
                                    <td className="py-2 px-3">{r.expected_action || '-'}</td>
                                </tr>
                            ))}
                            {!uxLogs.data?.length && uxLogs.status === 'ready' && (
                                <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={6}>موردی یافت نشد</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-4">
                <div>
                    <h3 className="font-bold text-gray-800">کاربران (Global) + خروجی اکسل</h3>
                    <p className="text-sm text-gray-500 mt-1">نمایش/خروجی فقط برای سوپرادمین فعال است.</p>
                </div>

                <div className="mt-4 grid grid-cols-1 lg:grid-cols-4 gap-3">
                    <select
                        className="border rounded-xl px-3 py-2 bg-white"
                        value={globalRepresentativeId == null ? '' : String(globalRepresentativeId)}
                        onChange={(e) => setGlobalRepresentativeId(e.target.value ? Number(e.target.value) : null)}
                    >
                        <option value="">همه نماینده‌ها</option>
                        {candidates.map((c) => (
                            <option key={c.id} value={String(c.id)}>
                                {c.name}
                            </option>
                        ))}
                    </select>

                    <input
                        className="border rounded-xl px-3 py-2 bg-white"
                        type="date"
                        value={globalStartDate}
                        onChange={(e) => setGlobalStartDate(e.target.value)}
                    />
                    <input
                        className="border rounded-xl px-3 py-2 bg-white"
                        type="date"
                        value={globalEndDate}
                        onChange={(e) => setGlobalEndDate(e.target.value)}
                    />
                    <select
                        className="border rounded-xl px-3 py-2 bg-white"
                        value={globalInteractionType}
                        onChange={(e) => setGlobalInteractionType(e.target.value as any)}
                    >
                        <option value="">همه تعامل‌ها</option>
                        <option value="question">سوال</option>
                        <option value="comment">نظر</option>
                        <option value="lead">سرنخ</option>
                    </select>
                </div>

                <div className="mt-3 flex flex-col sm:flex-row gap-2">
                    <button
                        className="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm"
                        onClick={loadGlobalUsers}
                    >
                        نمایش
                    </button>
                    <button
                        className={`px-3 py-2 rounded-xl text-sm ${isExporting ? 'bg-gray-200 text-gray-500' : 'bg-gray-900 hover:bg-black text-white'}`}
                        disabled={isExporting}
                        onClick={exportGlobalUsers}
                    >
                        {isExporting ? 'در حال خروجی...' : 'خروجی اکسل'}
                    </button>
                </div>

                {globalUsers.status === 'loading' && <div className="mt-3 text-sm text-gray-500">در حال بارگذاری...</div>}
                {globalUsers.error && <div className="mt-3 text-sm text-red-600">{globalUsers.error}</div>}

                <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="text-right text-gray-500">
                                <th className="py-2 px-3">کاربر</th>
                                <th className="py-2 px-3">نام</th>
                                <th className="py-2 px-3">تلفن</th>
                                <th className="py-2 px-3">نماینده</th>
                                <th className="py-2 px-3">اولین تعامل</th>
                                <th className="py-2 px-3">آخرین تعامل</th>
                                <th className="py-2 px-3">تعداد</th>
                                <th className="py-2 px-3">Flags</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(globalUsers.data || []).map((u, idx) => (
                                <tr key={`${u.user_id}-${idx}`} className="border-t">
                                    <td className="py-2 px-3" dir="ltr">{u.user_id}</td>
                                    <td className="py-2 px-3">{[u.first_name, u.last_name].filter(Boolean).join(' ') || u.username || '-'}</td>
                                    <td className="py-2 px-3" dir="ltr">{u.phone || '-'}</td>
                                    <td className="py-2 px-3">{u.representative_id}</td>
                                    <td className="py-2 px-3" dir="ltr">{formatDateTime(u.first_interaction_at)}</td>
                                    <td className="py-2 px-3" dir="ltr">{formatDateTime(u.last_interaction_at)}</td>
                                    <td className="py-2 px-3">{u.total_interactions}</td>
                                    <td className="py-2 px-3 text-xs">
                                        {u.asked_question ? 'Q ' : ''}
                                        {u.left_comment ? 'C ' : ''}
                                        {u.viewed_commitment ? 'K ' : ''}
                                        {u.became_lead ? 'L ' : ''}
                                    </td>
                                </tr>
                            ))}
                            {!globalUsers.data?.length && globalUsers.status === 'ready' && (
                                <tr className="border-t"><td className="py-2 px-3 text-gray-500" colSpan={8}>موردی یافت نشد</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default MvpLearningTab;
