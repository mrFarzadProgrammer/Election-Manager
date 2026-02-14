import React, { useEffect, useMemo, useState } from 'react';
import { CandidateData, Commitment, CommitmentStatus } from '../../../types';
import { api } from '../../../services/api';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';
import ConfirmModal from '../ui/ConfirmModal';
import { CheckCircle2, FileText, PlusCircle, RefreshCw, ShieldAlert, Trash2, UploadCloud } from 'lucide-react';

interface CommitmentsV1Props {
    candidate: CandidateData;
}

const CATEGORY_OPTIONS = [
    { value: 'economy', label: 'اقتصاد و معیشت' },
    { value: 'employment', label: 'اشتغال' },
    { value: 'housing', label: 'مسکن' },
    { value: 'transparency', label: 'شفافیت' },
    { value: 'other', label: 'سایر' },
] as const;

const statusMeta = (s: CommitmentStatus) => {
    if (s === 'draft') return { label: 'پیش‌نویس', cls: 'bg-gray-50 text-gray-700 border-gray-200' };
    if (s === 'active') return { label: 'فعال', cls: 'bg-blue-50 text-blue-700 border-blue-200' };
    if (s === 'in_progress') return { label: 'در حال اجرا', cls: 'bg-amber-50 text-amber-700 border-amber-200' };
    if (s === 'completed') return { label: 'انجام‌شده', cls: 'bg-green-50 text-green-700 border-green-200' };
    return { label: 'ناموفق', cls: 'bg-rose-50 text-rose-700 border-rose-200' };
};

const toFaDateTime = (iso: string | null | undefined) => {
    if (!iso) return '';
    const d = new Date(String(iso));
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('fa-IR');
};

const catLabel = (value: any) => {
    const v = String(value || '').trim();
    const found = CATEGORY_OPTIONS.find((x) => x.value === v);
    return found ? found.label : (v || '');
};

const isPublished = (c: Commitment) => !!c.published_at || c.is_locked || c.status !== 'draft';

const CommitmentsV1: React.FC<CommitmentsV1Props> = ({ candidate }) => {
    const [accepted, setAccepted] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState(false);
    const [items, setItems] = useState<Commitment[]>([]);

    const [modal, setModal] = useState<null | { variant: ResultModalVariant; title: string; message: string }>(null);

    const [acceptChecked, setAcceptChecked] = useState(false);
    const [isAccepting, setIsAccepting] = useState(false);

    const [newTitle, setNewTitle] = useState('');
    const [newDesc, setNewDesc] = useState('');
    const [newCat, setNewCat] = useState<(typeof CATEGORY_OPTIONS)[number]['value']>('economy');
    const [isCreating, setIsCreating] = useState(false);

    const [draftEdits, setDraftEdits] = useState<Record<number, { title: string; description: string; category: string }>>({});
    const [savingId, setSavingId] = useState<number | null>(null);

    const [statusEdits, setStatusEdits] = useState<Record<number, CommitmentStatus>>({});
    const [progressDraft, setProgressDraft] = useState<Record<number, string>>({});
    const [busyId, setBusyId] = useState<number | null>(null);

    const [confirm, setConfirm] = useState<
        | null
        | { kind: 'publish' | 'deleteDraft'; commitmentId: number; title: string; message: string; confirmLabel: string }
    >(null);

    const getToken = () => localStorage.getItem('access_token') || '';

    const load = async () => {
        const token = getToken();
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }

        setIsLoading(true);
        try {
            const a = await api.getMyCommitmentTermsAcceptance(token);
            setAccepted(!!a);
            if (a) {
                const list = await api.getMyCommitments(token);
                setItems(list || []);

                setDraftEdits((prev) => {
                    const next = { ...prev };
                    for (const c of list || []) {
                        if (c.status === 'draft' && next[c.id] === undefined) {
                            next[c.id] = {
                                title: c.title || '',
                                description: c.description || '',
                                category: String(c.category || 'other'),
                            };
                        }
                    }
                    return next;
                });

                setStatusEdits((prev) => {
                    const next = { ...prev };
                    for (const c of list || []) {
                        if (isPublished(c) && next[c.id] === undefined) {
                            next[c.id] = c.status;
                        }
                    }
                    return next;
                });

                setProgressDraft((prev) => {
                    const next = { ...prev };
                    for (const c of list || []) {
                        if (isPublished(c) && next[c.id] === undefined) next[c.id] = '';
                    }
                    return next;
                });
            } else {
                setItems([]);
            }
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در دریافت اطلاعات' });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        void load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [candidate.id]);

    const sortedItems = useMemo(() => {
        return [...(items || [])].sort((a, b) => (b.id || 0) - (a.id || 0));
    }, [items]);

    const doAccept = async () => {
        const token = getToken();
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }
        if (!acceptChecked) {
            setModal({ variant: 'warning', title: 'نیاز به تأیید', message: 'برای ادامه باید موارد را تأیید کنید.' });
            return;
        }

        setIsAccepting(true);
        try {
            await api.acceptMyCommitmentTerms(token);
            setAccepted(true);
            setModal({ variant: 'success', title: 'ثبت شد', message: 'تأییدیه شما ثبت شد.' });
            await load();
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در ثبت تأییدیه' });
        } finally {
            setIsAccepting(false);
        }
    };

    const doCreate = async () => {
        const token = getToken();
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }
        const title = newTitle.trim();
        const description = newDesc.trim();
        if (!title || !description) {
            setModal({ variant: 'warning', title: 'اطلاعات ناقص', message: 'عنوان و توضیحات الزامی است.' });
            return;
        }

        setIsCreating(true);
        try {
            await api.createMyCommitmentDraft(token, { title, description, category: newCat });
            setNewTitle('');
            setNewDesc('');
            setNewCat('economy');
            await load();
            setModal({ variant: 'success', title: 'ایجاد شد', message: 'تعهد به‌صورت پیش‌نویس ایجاد شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در ایجاد تعهد' });
        } finally {
            setIsCreating(false);
        }
    };

    const doSaveDraft = async (commitmentId: number) => {
        const token = getToken();
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }
        const patch = draftEdits[commitmentId];
        if (!patch) return;

        const title = (patch.title || '').trim();
        const description = (patch.description || '').trim();
        const category = String(patch.category || '').trim();

        if (!title || !description || !category) {
            setModal({ variant: 'warning', title: 'اطلاعات ناقص', message: 'عنوان، توضیحات و دسته‌بندی الزامی است.' });
            return;
        }

        setSavingId(commitmentId);
        try {
            await api.updateMyCommitmentDraft(token, commitmentId, { title, description, category });
            await load();
            setModal({ variant: 'success', title: 'ذخیره شد', message: 'پیش‌نویس ذخیره شد.' });
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در ذخیره' });
        } finally {
            setSavingId(null);
        }
    };

    const openPublishConfirm = (commitmentId: number) => {
        setConfirm({
            kind: 'publish',
            commitmentId,
            title: 'انتشار تعهد',
            message: 'پس از انتشار، متن و دسته‌بندی این تعهد غیرقابل ویرایش و غیرقابل حذف خواهد بود. فقط امکان ثبت وضعیت و گزارش پیشرفت وجود دارد. آیا مطمئن هستید؟',
            confirmLabel: 'انتشار',
        });
    };

    const openDeleteConfirm = (commitmentId: number) => {
        setConfirm({
            kind: 'deleteDraft',
            commitmentId,
            title: 'حذف پیش‌نویس',
            message: 'این پیش‌نویس حذف می‌شود. این عملیات قابل بازگشت نیست. ادامه می‌دهید؟',
            confirmLabel: 'حذف',
        });
    };

    const doConfirm = async () => {
        const token = getToken();
        if (!token) {
            setConfirm(null);
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }
        if (!confirm) return;
        const id = confirm.commitmentId;

        setBusyId(id);
        try {
            if (confirm.kind === 'publish') {
                await api.publishMyCommitment(token, id);
                setModal({ variant: 'success', title: 'منتشر شد', message: 'تعهد منتشر و قفل شد.' });
            } else {
                await api.deleteMyCommitmentDraft(token, id);
                setModal({ variant: 'success', title: 'حذف شد', message: 'پیش‌نویس حذف شد.' });
            }
            setConfirm(null);
            await load();
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در انجام عملیات' });
        } finally {
            setBusyId(null);
        }
    };

    const doUpdateStatus = async (commitmentId: number) => {
        const token = getToken();
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }
        const status = statusEdits[commitmentId];
        if (!status) return;

        setBusyId(commitmentId);
        try {
            await api.updateMyCommitmentStatus(token, commitmentId, status);
            setModal({ variant: 'success', title: 'ثبت شد', message: 'وضعیت تعهد به‌روزرسانی شد.' });
            await load();
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در ثبت وضعیت' });
        } finally {
            setBusyId(null);
        }
    };

    const doAddProgress = async (commitmentId: number) => {
        const token = getToken();
        if (!token) {
            setModal({ variant: 'warning', title: 'نیاز به ورود', message: 'ابتدا وارد حساب کاربری شوید.' });
            return;
        }
        const note = (progressDraft[commitmentId] || '').trim();
        if (!note) {
            setModal({ variant: 'warning', title: 'متن خالی', message: 'متن گزارش پیشرفت را وارد کنید.' });
            return;
        }

        setBusyId(commitmentId);
        try {
            await api.addMyCommitmentProgressLog(token, commitmentId, note);
            setProgressDraft((prev) => ({ ...prev, [commitmentId]: '' }));
            setModal({ variant: 'success', title: 'ثبت شد', message: 'گزارش پیشرفت ثبت شد.' });
            await load();
        } catch (e: any) {
            setModal({ variant: 'error', title: 'خطا', message: e?.message || 'خطا در ثبت گزارش' });
        } finally {
            setBusyId(null);
        }
    };

    return (
        <div className="space-y-4">
            <ResultModal
                open={!!modal}
                variant={modal?.variant || 'info'}
                title={modal?.title || ''}
                message={modal?.message || ''}
                onClose={() => setModal(null)}
            />

            <ConfirmModal
                open={!!confirm}
                variant={confirm?.kind === 'deleteDraft' ? 'error' : 'warning'}
                title={confirm?.title || ''}
                message={confirm?.message || ''}
                confirmLabel={confirm?.confirmLabel || 'تأیید'}
                cancelLabel="انصراف"
                onConfirm={doConfirm}
                onCancel={() => setConfirm(null)}
            />

            <div className="bg-white rounded-2xl shadow-sm border p-6">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-blue-700">
                            <FileText size={18} />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-gray-800">تعهدات (قراردادهای عمومی)</h3>
                            <p className="text-xs text-gray-500 mt-1">تعهد پس از انتشار قفل می‌شود و غیرقابل ویرایش است.</p>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={() => void load()}
                        disabled={isLoading}
                        className="px-3 py-2 rounded-xl text-gray-700 bg-gray-100 hover:bg-gray-200 transition flex items-center gap-2"
                    >
                        <RefreshCw size={16} />
                        بروزرسانی
                    </button>
                </div>
            </div>

            {!accepted ? (
                <div className="bg-white rounded-2xl shadow-sm border p-6">
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-700">
                            <ShieldAlert size={18} />
                        </div>
                        <div className="flex-1">
                            <h4 className="text-sm font-bold text-gray-800">نکات مهم قبل از ایجاد تعهد</h4>
                            <ul className="mt-2 text-sm text-gray-600 leading-7 list-disc pr-5">
                                <li>تعهد پس از انتشار، غیرقابل ویرایش و غیرقابل حذف است.</li>
                                <li>بعد از انتشار فقط می‌توانید وضعیت را تغییر دهید و گزارش‌های پیشرفت را به‌صورت افزایشی ثبت کنید.</li>
                                <li>گزارش‌های پیشرفت به تاریخ ثبت می‌شوند و پاک نمی‌گردند.</li>
                            </ul>

                            <label className="mt-4 flex items-center gap-2 text-sm text-gray-700 select-none">
                                <input
                                    type="checkbox"
                                    className="w-4 h-4"
                                    checked={acceptChecked}
                                    onChange={(e) => setAcceptChecked(e.target.checked)}
                                />
                                موارد بالا را مطالعه کرده‌ام و می‌پذیرم.
                            </label>

                            <div className="mt-4">
                                <button
                                    type="button"
                                    disabled={!acceptChecked || isAccepting}
                                    onClick={() => void doAccept()}
                                    className="px-5 py-2.5 rounded-xl font-medium bg-amber-600 text-white hover:bg-amber-700 transition disabled:opacity-50"
                                >
                                    {isAccepting ? 'در حال ثبت...' : 'می‌پذیرم و ادامه می‌دهم'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    <div className="bg-white rounded-2xl shadow-sm border p-6">
                        <div className="flex items-center justify-between gap-3 mb-4">
                            <h4 className="text-sm font-bold text-gray-800">ایجاد تعهد جدید (پیش‌نویس)</h4>
                            <div className="text-xs text-gray-500">ابتدا به‌صورت پیش‌نویس ایجاد کنید، سپس منتشر کنید.</div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div className="md:col-span-2">
                                <label className="text-xs text-gray-500">عنوان</label>
                                <input
                                    value={newTitle}
                                    onChange={(e) => setNewTitle(e.target.value)}
                                    className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
                                    placeholder="مثلاً: انتشار گزارش مالی ماهانه"
                                />
                            </div>

                            <div>
                                <label className="text-xs text-gray-500">دسته‌بندی</label>
                                <select
                                    value={newCat}
                                    onChange={(e) => setNewCat(e.target.value as any)}
                                    className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
                                >
                                    {CATEGORY_OPTIONS.map((x) => (
                                        <option key={x.value} value={x.value}>
                                            {x.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="md:col-span-3">
                                <label className="text-xs text-gray-500">توضیحات</label>
                                <textarea
                                    value={newDesc}
                                    onChange={(e) => setNewDesc(e.target.value)}
                                    className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white min-h-[110px] focus:outline-none focus:ring-2 focus:ring-blue-200"
                                    placeholder="جزئیات تعهد را دقیق و قابل سنجش بنویسید..."
                                />
                            </div>
                        </div>

                        <div className="mt-4 flex justify-end">
                            <button
                                type="button"
                                onClick={() => void doCreate()}
                                disabled={isCreating}
                                className="px-5 py-2.5 rounded-xl font-medium bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50 flex items-center gap-2"
                            >
                                <PlusCircle size={18} />
                                {isCreating ? 'در حال ایجاد...' : 'ایجاد پیش‌نویس'}
                            </button>
                        </div>
                    </div>

                    <div className="space-y-3">
                        {sortedItems.length === 0 ? (
                            <div className="bg-white rounded-2xl shadow-sm border p-6 text-sm text-gray-600">
                                هنوز تعهدی ثبت نشده است.
                            </div>
                        ) : (
                            sortedItems.map((c) => {
                                const meta = statusMeta(c.status);
                                const published = isPublished(c);
                                const progress = [...(c.progress_logs || [])].sort((a, b) => (b.id || 0) - (a.id || 0));

                                return (
                                    <div key={c.id} className="bg-white rounded-2xl shadow-sm border p-6">
                                        <div className="flex flex-wrap items-start justify-between gap-3">
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <h5 className="text-sm font-bold text-gray-800">{c.title}</h5>
                                                    <span className={`text-[11px] px-2 py-1 rounded-full border ${meta.cls}`}>{meta.label}</span>
                                                    {published && (
                                                        <span className="text-[11px] px-2 py-1 rounded-full border bg-gray-50 text-gray-700 border-gray-200">قفل‌شده</span>
                                                    )}
                                                </div>
                                                <div className="text-xs text-gray-500 mt-1">
                                                    دسته‌بندی: {catLabel(c.category)}
                                                    {c.published_at ? ` • انتشار: ${toFaDateTime(c.published_at)}` : ''}
                                                    {c.created_at ? ` • ایجاد: ${toFaDateTime(c.created_at)}` : ''}
                                                </div>
                                            </div>

                                            {c.status === 'draft' ? (
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => openDeleteConfirm(c.id)}
                                                        disabled={busyId === c.id}
                                                        className="px-3 py-2 rounded-xl bg-rose-50 text-rose-700 hover:bg-rose-100 transition flex items-center gap-2 disabled:opacity-50"
                                                    >
                                                        <Trash2 size={16} />
                                                        حذف
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => openPublishConfirm(c.id)}
                                                        disabled={busyId === c.id}
                                                        className="px-3 py-2 rounded-xl bg-amber-600 text-white hover:bg-amber-700 transition flex items-center gap-2 disabled:opacity-50"
                                                    >
                                                        <UploadCloud size={16} />
                                                        انتشار
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="text-xs text-gray-500 flex items-center gap-2">
                                                    <CheckCircle2 size={16} className="text-gray-400" />
                                                    فقط وضعیت/گزارش قابل افزودن است
                                                </div>
                                            )}
                                        </div>

                                        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                                            <div className="md:col-span-2">
                                                <label className="text-xs text-gray-500">عنوان</label>
                                                <input
                                                    value={c.status === 'draft' ? (draftEdits[c.id]?.title ?? c.title) : c.title}
                                                    onChange={(e) =>
                                                        setDraftEdits((prev) => ({
                                                            ...prev,
                                                            [c.id]: {
                                                                title: e.target.value,
                                                                description: prev[c.id]?.description ?? c.description,
                                                                category: prev[c.id]?.category ?? String(c.category || 'other'),
                                                            },
                                                        }))
                                                    }
                                                    disabled={c.status !== 'draft'}
                                                    className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white disabled:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200"
                                                />
                                            </div>

                                            <div>
                                                <label className="text-xs text-gray-500">دسته‌بندی</label>
                                                <select
                                                    value={c.status === 'draft' ? (draftEdits[c.id]?.category ?? String(c.category || 'other')) : String(c.category || 'other')}
                                                    onChange={(e) =>
                                                        setDraftEdits((prev) => ({
                                                            ...prev,
                                                            [c.id]: {
                                                                title: prev[c.id]?.title ?? c.title,
                                                                description: prev[c.id]?.description ?? c.description,
                                                                category: e.target.value,
                                                            },
                                                        }))
                                                    }
                                                    disabled={c.status !== 'draft'}
                                                    className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white disabled:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200"
                                                >
                                                    {CATEGORY_OPTIONS.map((x) => (
                                                        <option key={x.value} value={x.value}>
                                                            {x.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            <div className="md:col-span-3">
                                                <label className="text-xs text-gray-500">توضیحات</label>
                                                <textarea
                                                    value={
                                                        c.status === 'draft'
                                                            ? (draftEdits[c.id]?.description ?? c.description)
                                                            : c.description
                                                    }
                                                    onChange={(e) =>
                                                        setDraftEdits((prev) => ({
                                                            ...prev,
                                                            [c.id]: {
                                                                title: prev[c.id]?.title ?? c.title,
                                                                description: e.target.value,
                                                                category: prev[c.id]?.category ?? String(c.category || 'other'),
                                                            },
                                                        }))
                                                    }
                                                    disabled={c.status !== 'draft'}
                                                    className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white min-h-[110px] disabled:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-200"
                                                />
                                            </div>
                                        </div>

                                        {c.status === 'draft' ? (
                                            <div className="mt-4 flex justify-end">
                                                <button
                                                    type="button"
                                                    onClick={() => void doSaveDraft(c.id)}
                                                    disabled={savingId === c.id}
                                                    className="px-5 py-2.5 rounded-xl font-medium bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50"
                                                >
                                                    {savingId === c.id ? 'در حال ذخیره...' : 'ذخیره پیش‌نویس'}
                                                </button>
                                            </div>
                                        ) : (
                                            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                                                <div>
                                                    <label className="text-xs text-gray-500">وضعیت</label>
                                                    <select
                                                        value={statusEdits[c.id] || c.status}
                                                        onChange={(e) => setStatusEdits((prev) => ({ ...prev, [c.id]: e.target.value as any }))}
                                                        className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
                                                    >
                                                        <option value="active">فعال</option>
                                                        <option value="in_progress">در حال اجرا</option>
                                                        <option value="completed">انجام‌شده</option>
                                                        <option value="failed">ناموفق</option>
                                                    </select>
                                                </div>
                                                <div className="md:col-span-2 flex items-end justify-end">
                                                    <button
                                                        type="button"
                                                        onClick={() => void doUpdateStatus(c.id)}
                                                        disabled={busyId === c.id}
                                                        className="px-5 py-2.5 rounded-xl font-medium bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50"
                                                    >
                                                        {busyId === c.id ? 'در حال ثبت...' : 'ثبت وضعیت'}
                                                    </button>
                                                </div>

                                                <div className="md:col-span-3">
                                                    <label className="text-xs text-gray-500">گزارش پیشرفت (افزایشی)</label>
                                                    <textarea
                                                        value={progressDraft[c.id] || ''}
                                                        onChange={(e) => setProgressDraft((prev) => ({ ...prev, [c.id]: e.target.value }))}
                                                        className="mt-1 w-full px-3 py-2.5 rounded-xl border bg-white min-h-[90px] focus:outline-none focus:ring-2 focus:ring-blue-200"
                                                        placeholder="مثلاً: در تاریخ ... جلسه با ... برگزار شد و ..."
                                                    />
                                                    <div className="mt-3 flex justify-end">
                                                        <button
                                                            type="button"
                                                            onClick={() => void doAddProgress(c.id)}
                                                            disabled={busyId === c.id}
                                                            className="px-5 py-2.5 rounded-xl font-medium bg-amber-600 text-white hover:bg-amber-700 transition disabled:opacity-50"
                                                        >
                                                            {busyId === c.id ? 'در حال ثبت...' : 'ثبت گزارش پیشرفت'}
                                                        </button>
                                                    </div>
                                                </div>

                                                <div className="md:col-span-3">
                                                    <div className="text-xs font-bold text-gray-700 mb-2">گزارش‌های ثبت‌شده</div>
                                                    {progress.length === 0 ? (
                                                        <div className="text-sm text-gray-600">هنوز گزارشی ثبت نشده است.</div>
                                                    ) : (
                                                        <div className="space-y-2">
                                                            {progress.map((p) => (
                                                                <div key={p.id} className="border rounded-xl p-3 bg-gray-50">
                                                                    <div className="text-[11px] text-gray-500 mb-1">{toFaDateTime(p.created_at)}</div>
                                                                    <div className="text-sm text-gray-700 leading-7 whitespace-pre-wrap">{p.note}</div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

export default CommitmentsV1;
