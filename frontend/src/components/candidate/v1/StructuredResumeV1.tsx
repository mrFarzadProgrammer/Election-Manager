import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CandidateData } from '../../../types';
import { Save, FileText, Plus, Trash2 } from 'lucide-react';
import ResultModal, { ResultModalVariant } from '../ui/ResultModal';

interface StructuredResumeV1Props {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

type StructuredResume = {
    education: string[];
    executive: string[];
    social: string[];
};

type SectionProps = {
    title: string;
    items: string[];
    onAdd: () => void;
    onRemove: (idx: number) => void;
    placeholder: string;
    value: string;
    onChange: (nextValue: string) => void;
};

const Section: React.FC<SectionProps> = (props) => (
    <div className="bg-gray-50 border border-gray-100 rounded-2xl p-4">
        <h4 className="text-sm font-bold text-gray-700 mb-3">{props.title}</h4>

        <div className="flex flex-col sm:flex-row gap-2">
            <input
                value={props.value}
                onChange={(e) => props.onChange(e.target.value)}
                className="flex-1 border rounded-xl px-4 py-2 bg-white"
                placeholder={props.placeholder}
            />
            <button
                onClick={props.onAdd}
                type="button"
                className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition"
            >
                <Plus size={16} />
                افزودن
            </button>
        </div>

        <div className="mt-3 space-y-2">
            {props.items.length === 0 ? (
                <p className="text-xs text-gray-400">موردی ثبت نشده است.</p>
            ) : (
                props.items.map((item, idx) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-xl px-3 py-2 flex items-start justify-between gap-3">
                        <div className="text-sm text-gray-700 flex-1 whitespace-pre-wrap break-words">{item}</div>
                        <button
                            onClick={() => props.onRemove(idx)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                            aria-label="حذف"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>
                ))
            )}
        </div>
    </div>
);

const asStringArray = (value: any): string[] => {
    if (!Array.isArray(value)) return [];
    return value.map((v) => String(v || '').trim()).filter(Boolean);
};

const StructuredResumeV1: React.FC<StructuredResumeV1Props> = ({ candidate, onUpdate }) => {
    const initialStructured = useMemo(() => {
        const botConfig = candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {};
        const sr = (botConfig as any).structured_resume;
        // Backward/forward compatibility: earlier versions used `experience`.
        // V1 panel uses `executive` and `social`.
        const executiveRaw = sr?.executive ?? sr?.experience;
        const structured: StructuredResume = {
            education: asStringArray(sr?.education),
            executive: asStringArray(executiveRaw),
            social: asStringArray(sr?.social),
        };
        return structured;
    }, [candidate.bot_config]);

    const [education, setEducation] = useState<string[]>(initialStructured.education);
    const [executive, setExecutive] = useState<string[]>(initialStructured.executive);
    const [social, setSocial] = useState<string[]>(initialStructured.social);

    const [eduDraft, setEduDraft] = useState('');
    const [execDraft, setExecDraft] = useState('');
    const [socialDraft, setSocialDraft] = useState('');

    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const [saveStatus, setSaveStatus] = useState<string | null>(null);
    const [saveModal, setSaveModal] = useState<null | { title: string; message: string; variant: ResultModalVariant }>(null);
    const lastCandidateIdRef = useRef<string>(candidate.id);
    const lastStructuredSignatureRef = useRef<string>('');

    const currentStructuredSignature = useMemo(() => {
        const botConfig = candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {};
        const sr = (botConfig as any).structured_resume;
        const executiveRaw = sr?.executive ?? sr?.experience;
        const normalized: StructuredResume = {
            education: asStringArray(sr?.education),
            executive: asStringArray(executiveRaw),
            social: asStringArray(sr?.social),
        };
        return JSON.stringify(normalized);
    }, [candidate.bot_config]);

    useEffect(() => {
        const candidateChanged = lastCandidateIdRef.current !== candidate.id;
        if (candidateChanged) {
            lastCandidateIdRef.current = candidate.id;
            lastStructuredSignatureRef.current = '';
            setIsDirty(false);
            setSaveStatus(null);
            setEduDraft('');
            setExecDraft('');
            setSocialDraft('');
        }

        // Avoid clobbering local edits while user has unsaved changes.
        if (isDirty) return;

        // Candidate objects can refresh frequently (polling). Only resync when data actually changed.
        if (lastStructuredSignatureRef.current === currentStructuredSignature) return;
        lastStructuredSignatureRef.current = currentStructuredSignature;

        try {
            const parsed = JSON.parse(currentStructuredSignature) as StructuredResume;
            setEducation(parsed.education);
            setExecutive(parsed.executive);
            setSocial(parsed.social);
        } catch {
            // ignore
        }
    }, [candidate.id, currentStructuredSignature, isDirty]);

    const saveStructured = async (next: StructuredResume) => {
        setIsSaving(true);
        setSaveStatus('در حال ذخیره...');
        try {
            const bot_config = {
                ...(candidate.bot_config && typeof candidate.bot_config === 'object' ? candidate.bot_config : {}),
                structured_resume: {
                    education: next.education,
                    executive: next.executive,
                    social: next.social,
                    // Keep a mirror field for bot/older code paths that expect `experience`.
                    experience: next.executive,
                },
            };

            await onUpdate({ bot_config });
            setIsDirty(false);
            setSaveStatus('ذخیره شد');
            setSaveModal({
                title: 'ذخیره شد',
                message: 'تغییرات با موفقیت ذخیره شد.',
                variant: 'success',
            });
        } catch (e: any) {
            setSaveStatus(null);
            setSaveModal({
                title: 'خطا در ذخیره',
                message: e?.message || 'خطا در ذخیره',
                variant: 'error',
            });
        } finally {
            setIsSaving(false);
        }
    };

    const addItem = (kind: 'education' | 'executive' | 'social') => {
        if (kind === 'education') {
            const v = eduDraft.trim();
            if (!v) return;
            setEducation((prev) => [...prev, v]);
            setEduDraft('');
            setIsDirty(true);
            setSaveStatus(null);
            return;
        }
        if (kind === 'executive') {
            const v = execDraft.trim();
            if (!v) return;
            setExecutive((prev) => [...prev, v]);
            setExecDraft('');
            setIsDirty(true);
            setSaveStatus(null);
            return;
        }
        if (kind === 'social') {
            const v = socialDraft.trim();
            if (!v) return;
            setSocial((prev) => [...prev, v]);
            setSocialDraft('');
            setIsDirty(true);
            setSaveStatus(null);
            return;
        }
    };

    const removeItem = (kind: 'education' | 'executive' | 'social', index: number) => {
        setIsDirty(true);
        setSaveStatus(null);
        if (kind === 'education') {
            const nextEducation = education.filter((_, i) => i !== index);
            setEducation(nextEducation);
            return;
        }
        if (kind === 'executive') {
            const nextExecutive = executive.filter((_, i) => i !== index);
            setExecutive(nextExecutive);
            return;
        }
        if (kind === 'social') {
            const nextSocial = social.filter((_, i) => i !== index);
            setSocial(nextSocial);
        }
    };

    const handleManualSave = async () => {
        await saveStructured({ education, executive, social });
    };

    return (
        <div className="space-y-6">
            <ResultModal
                open={!!saveModal}
                variant={saveModal?.variant || 'info'}
                title={saveModal?.title || ''}
                message={saveModal?.message || ''}
                onClose={() => setSaveModal(null)}
            />
            <div className="bg-white p-6 rounded-2xl shadow-sm border">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <FileText size={20} className="text-blue-600" />
                    سوابق (ساختاریافته)
                </h3>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Section
                        title="تحصیلات"
                        items={education}
                        onAdd={() => addItem('education')}
                        onRemove={(idx) => removeItem('education', idx)}
                        placeholder="مثلاً: کارشناسی ارشد حقوق"
                        value={eduDraft}
                        onChange={setEduDraft}
                    />

                    <Section
                        title="سابقه اجرایی"
                        items={executive}
                        onAdd={() => addItem('executive')}
                        onRemove={(idx) => removeItem('executive', idx)}
                        placeholder="مثلاً: مدیرکل ..."
                        value={execDraft}
                        onChange={setExecDraft}
                    />

                    <Section
                        title="سابقه اجتماعی / مردمی"
                        items={social}
                        onAdd={() => addItem('social')}
                        onRemove={(idx) => removeItem('social', idx)}
                        placeholder="مثلاً: عضو هیئت امنای ..."
                        value={socialDraft}
                        onChange={setSocialDraft}
                    />
                </div>

                <div className="flex items-center justify-between mt-6 gap-3">
                    <div className="text-xs text-gray-500">
                        {saveStatus ? saveStatus : isDirty ? 'تغییرات ذخیره نشده است' : ''}
                    </div>
                    <button
                        onClick={handleManualSave}
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

export default StructuredResumeV1;
