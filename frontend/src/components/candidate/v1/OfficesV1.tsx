import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Save, MapPin, Plus, Trash2 } from 'lucide-react';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface OfficesV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

type Office = {
    title: string;
    address: string;
    note?: string;
};

const MAX_OFFICES = 3;

const readOffices = (candidate: CandidateData): Office[] => {
    const botConfig = candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {};
    const raw = (botConfig as any).offices;
    if (!Array.isArray(raw)) return [];
    return raw
        .filter(Boolean)
        .slice(0, MAX_OFFICES)
        .map((o: any) => ({
            title: String(o?.title || '').trim(),
            address: String(o?.address || '').trim(),
            note: String(o?.note || '').trim(),
        }));
};

const OfficesV1: React.FC<OfficesV1Props> = ({ candidate, onUpdate }) => {
    const [offices, setOffices] = useState<Office[]>(useMemo(() => readOffices(candidate), [candidate]));
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
            setOffices(readOffices(candidate));
        }
    }, [candidate, isDirty]);

    const addOffice = () => {
        if (offices.length >= MAX_OFFICES) {
            setModal({ variant: 'warning', title: 'محدودیت', message: `حداکثر ${MAX_OFFICES} ستاد قابل ثبت است.` });
            return;
        }
        setIsDirty(true);
        setOffices((prev) => [...prev, { title: '', address: '', note: '' }]);
    };

    const removeOffice = (idx: number) => {
        setIsDirty(true);
        setOffices((prev) => prev.filter((_, i) => i !== idx));
    };

    const updateOffice = (idx: number, patch: Partial<Office>) => {
        setIsDirty(true);
        setOffices((prev) => prev.map((o, i) => (i === idx ? { ...o, ...patch } : o)));
    };

    const handleSave = async () => {
        if (offices.length > MAX_OFFICES) {
            setModal({ variant: 'warning', title: 'محدودیت', message: `حداکثر ${MAX_OFFICES} ستاد قابل ثبت است.` });
            return;
        }

        for (let i = 0; i < offices.length; i++) {
            const o = offices[i];
            if (!o.title.trim() || !o.address.trim()) {
                setModal({ variant: 'warning', title: 'اعتبارسنجی', message: `برای ستاد ${i + 1}، عنوان و آدرس الزامی است.` });
                return;
            }
        }

        setIsSaving(true);
        try {
            const normalized = offices.map((o) => ({
                title: o.title.trim(),
                address: o.address.trim(),
                note: (o.note || '').trim(),
            }));

            const bot_config = {
                ...(candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}),
                offices: normalized,
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
                <div className="flex items-center justify-between gap-3 mb-4">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <MapPin size={20} className="text-blue-600" />
                        ستادها (حداکثر ۳ مورد)
                    </h3>
                    <button
                        onClick={addOffice}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition"
                    >
                        <Plus size={16} />
                        افزودن ستاد
                    </button>
                </div>

                <div className="space-y-4">
                    {offices.length === 0 ? (
                        <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                            <p className="text-sm text-gray-500">هنوز ستادی ثبت نشده است.</p>
                        </div>
                    ) : (
                        offices.map((office, idx) => (
                            <div key={idx} className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-sm font-bold text-gray-700">ستاد {idx + 1}</p>
                                    <button
                                        onClick={() => removeOffice(idx)}
                                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                                        aria-label="حذف ستاد"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="flex flex-col gap-2">
                                        <label className="text-sm font-medium">عنوان ستاد</label>
                                        <input
                                            value={office.title}
                                            onChange={(e) => updateOffice(idx, { title: e.target.value })}
                                            className="border rounded-xl px-4 py-2 bg-white"
                                            placeholder="مثلاً: ستاد مرکزی"
                                        />
                                    </div>

                                    <div className="flex flex-col gap-2">
                                        <label className="text-sm font-medium">آدرس</label>
                                        <input
                                            value={office.address}
                                            onChange={(e) => updateOffice(idx, { address: e.target.value })}
                                            className="border rounded-xl px-4 py-2 bg-white"
                                            placeholder="آدرس کامل"
                                        />
                                    </div>

                                    <div className="flex flex-col gap-2 md:col-span-2">
                                        <label className="text-sm font-medium">توضیح کوتاه (ساعات / محله)</label>
                                        <input
                                            value={office.note || ''}
                                            onChange={(e) => updateOffice(idx, { note: e.target.value })}
                                            className="border rounded-xl px-4 py-2 bg-white"
                                            placeholder="مثلاً: ۹ تا ۱۸ / محله ..."
                                        />
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
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

export default OfficesV1;
