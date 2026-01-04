import React, { useState } from 'react';
import { Plan } from '../../types';
import { Plus, Edit, Eye, EyeOff, Check, X, Trash2 } from 'lucide-react';

interface PlansTabProps {
    plans: Plan[];
    onSavePlan: (plan: Partial<Plan>) => void;
    onDeletePlan: (id: string) => void;
}

const PlansTab: React.FC<PlansTabProps> = ({ plans, onSavePlan, onDeletePlan }) => {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingPlan, setEditingPlan] = useState<Partial<Plan>>({});

    const handleEdit = (plan?: Plan) => {
        setEditingPlan(plan || {
            title: '',
            price: '',
            description: '',
            features: [],
            color: '#3B82F6',
            is_visible: false
        });
        setIsModalOpen(true);
    };

    const handleSave = () => {
        if (!editingPlan.title || !editingPlan.price) {
            alert("لطفا عنوان و قیمت را وارد کنید");
            return;
        }

        // Clean up features
        const cleanedFeatures = (editingPlan.features || [])
            .map(f => f.trim())
            .filter(f => f.length > 0);

        console.log("Saving plan:", { ...editingPlan, features: cleanedFeatures });
        onSavePlan({
            ...editingPlan,
            features: cleanedFeatures
        });
        setIsModalOpen(false);
        setEditingPlan({});
    };

    const toggleVisibility = (plan: Plan) => {
        onSavePlan({ ...plan, is_visible: !plan.is_visible });
    };

    const colors = [
        '#64748b', // Slate (Silver-ish)
        '#cd7f32', // Bronze
        '#3b82f6', // Blue (Economy)
        '#22c55e', // Green (Basic)
        '#06b6d4', // Cyan (Special)
        '#6366f1', // Indigo (Diamond)
        '#ec4899', // Pink (Platinum)
        '#eab308', // Yellow (Gold)
        '#a855f7', // Purple (Parliament)
        '#14b8a6', // Teal (City Council)
        '#84cc16', // Lime (VIP)
    ];

    return (
        <div className='space-y-6'>
            <div className='flex justify-between items-center'>
                <h3 className='font-bold text-lg'>مدیریت پلن‌های اشتراک</h3>
                <button onClick={() => handleEdit()} className='flex items-center gap-2 bg-blue-900 text-white px-4 py-2 rounded-xl hover:bg-blue-800 transition'>
                    <Plus size={18} /> تعریف پلن
                </button>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
                {plans.map(plan => (
                    <div key={plan.id} className='bg-white rounded-3xl shadow-sm border overflow-hidden flex flex-col'>
                        {/* Header */}
                        <div style={{ backgroundColor: plan.color }} className='p-4 text-white relative h-24 flex flex-col items-center justify-center'>
                            <div className='absolute top-3 left-3 flex gap-2'>
                                <button onClick={() => onDeletePlan(plan.id)} className='text-white/80 hover:text-red-200 transition' title="حذف">
                                    <Trash2 size={16} />
                                </button>
                                <button onClick={() => handleEdit(plan)} className='text-white/80 hover:text-white transition' title="ویرایش">
                                    <Edit size={16} />
                                </button>
                                <button onClick={() => toggleVisibility(plan)} className='text-white/80 hover:text-white transition' title={plan.is_visible ? "مخفی کردن" : "نمایش"}>
                                    {plan.is_visible ? <Eye size={16} /> : <EyeOff size={16} />}
                                </button>
                            </div>
                            <h3 className='text-xl font-bold'>{plan.title}</h3>
                            <span className='text-xs bg-white/20 px-2 py-0.5 rounded-full mt-1'>اشتراک ماهانه</span>
                        </div>

                        {/* Price */}
                        <div className='py-6 text-center border-b border-gray-100'>
                            <div className='text-2xl font-bold text-gray-800'>
                                {Number(String(plan.price).replace(/,/g, '')).toLocaleString('fa-IR')} <span className='text-sm font-normal text-gray-500'>تومان</span>
                            </div>
                            {plan.created_at_jalali && (
                                <div className="text-[10px] text-gray-400 mt-2 font-mono">
                                    ایجاد: {plan.created_at_jalali}
                                </div>
                            )}
                        </div>

                        {/* Features */}
                        <div className='p-6 flex-grow'>
                            <div className='space-y-3'>
                                {(plan.features || []).map((f, i) => (
                                    <div key={i} className='flex items-center gap-2 text-sm text-gray-500'>
                                        <Check size={14} className='text-green-500 flex-shrink-0' />
                                        <span>{f}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl overflow-hidden">
                        <div className="flex justify-between items-center p-4 border-b bg-gray-50">
                            <h3 className="font-bold text-gray-800">{editingPlan.id ? 'ویرایش پلن' : 'تعریف پلن جدید'}</h3>
                            <button onClick={() => setIsModalOpen(false)} className="text-gray-500 hover:text-red-500 transition">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">عنوان پلن</label>
                                <input
                                    value={editingPlan.title || ''}
                                    onChange={e => setEditingPlan({ ...editingPlan, title: e.target.value })}
                                    className="w-full border border-gray-300 rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                                    placeholder="مثال: طرح طلایی"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">قیمت (تومان)</label>
                                <input
                                    type="text"
                                    value={editingPlan.price ? Number(String(editingPlan.price).replace(/,/g, '')).toLocaleString('en-US') : ''}
                                    onChange={e => {
                                        const val = e.target.value.replace(/,/g, '');
                                        if (!isNaN(Number(val))) {
                                            setEditingPlan({ ...editingPlan, price: val });
                                        }
                                    }}
                                    className="w-full border border-gray-300 rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                    placeholder="مثال: 1,000,000"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">توضیحات</label>
                                <textarea
                                    value={editingPlan.description || ''}
                                    onChange={e => setEditingPlan({ ...editingPlan, description: e.target.value })}
                                    className="w-full border border-gray-300 rounded-xl px-4 py-2 h-20 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition resize-none"
                                    placeholder="توضیحات مختصر درباره پلن..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">رنگ کارت</label>
                                <div className="flex flex-wrap gap-2 mb-2">
                                    {colors.map(c => (
                                        <button
                                            key={c}
                                            onClick={() => setEditingPlan({ ...editingPlan, color: c })}
                                            className={`w-8 h-8 rounded-full border-2 transition ${editingPlan.color === c ? 'border-gray-800 scale-110' : 'border-transparent hover:scale-105'}`}
                                            style={{ backgroundColor: c }}
                                        />
                                    ))}
                                </div>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="color"
                                        value={editingPlan.color || '#3b82f6'}
                                        onChange={e => setEditingPlan({ ...editingPlan, color: e.target.value })}
                                        className="h-9 w-14 p-0 border-0 rounded cursor-pointer"
                                    />
                                    <input
                                        type="text"
                                        value={editingPlan.color || ''}
                                        onChange={e => setEditingPlan({ ...editingPlan, color: e.target.value })}
                                        placeholder="#000000"
                                        className="flex-1 border border-gray-300 rounded-xl px-4 py-1.5 text-sm dir-ltr text-left focus:ring-2 focus:ring-blue-500 outline-none"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">ویژگی‌ها (هر خط یک ویژگی)</label>
                                <textarea
                                    value={Array.isArray(editingPlan.features) ? editingPlan.features.join('\n') : ''}
                                    onChange={e => setEditingPlan({ ...editingPlan, features: e.target.value.split('\n') })}
                                    className="w-full border border-gray-300 rounded-xl px-4 py-2 h-32 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition resize-none"
                                    placeholder="دسترسی به 500 کاربر&#10;پشتیبانی 24 ساعته&#10;..."
                                />
                            </div>

                            {/* Live Preview */}
                            <div className="mt-6 border-t pt-4">
                                <label className="block text-sm font-medium text-gray-700 mb-3">پیش‌نمایش زنده</label>
                                <div className='bg-white rounded-3xl shadow-sm border overflow-hidden flex flex-col max-w-[280px] mx-auto transform scale-90 origin-top'>
                                    {/* Header */}
                                    <div style={{ backgroundColor: editingPlan.color || '#3b82f6' }} className='p-4 text-white relative h-24 flex flex-col items-center justify-center'>
                                        <h3 className='text-xl font-bold'>{editingPlan.title || 'عنوان پلن'}</h3>
                                        <span className='text-xs bg-white/20 px-2 py-0.5 rounded-full mt-1'>اشتراک ماهانه</span>
                                    </div>

                                    {/* Price */}
                                    <div className='py-6 text-center border-b border-gray-100'>
                                        <div className='text-2xl font-bold text-gray-800'>
                                            {editingPlan.price ? Number(String(editingPlan.price).replace(/,/g, '')).toLocaleString('fa-IR') : '0'} <span className='text-sm font-normal text-gray-500'>تومان</span>
                                        </div>
                                    </div>

                                    {/* Features */}
                                    <div className='p-6 flex-grow bg-gray-50/50'>
                                        <div className='space-y-3'>
                                            {(editingPlan.features || []).filter(f => f.trim()).map((f, i) => (
                                                <div key={i} className='flex items-center gap-2 text-sm text-gray-500'>
                                                    <Check size={14} className='text-green-500 flex-shrink-0' />
                                                    <span>{f}</span>
                                                </div>
                                            ))}
                                            {(!editingPlan.features || editingPlan.features.length === 0) && (
                                                <div className="text-center text-gray-400 text-xs italic">ویژگی‌ها اینجا نمایش داده می‌شوند</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
                            <button onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-xl transition">انصراف</button>
                            <button onClick={handleSave} className="px-6 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-600/30 transition">
                                {editingPlan.id ? 'ذخیره تغییرات' : 'ایجاد پلن'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PlansTab;