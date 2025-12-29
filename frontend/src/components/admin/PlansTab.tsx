import React, { useState } from 'react';
import { Plan } from '../../types';
import { Plus, Edit, Trash2, Check } from 'lucide-react';

interface PlansTabProps {
    plans: Plan[];
    onSavePlan: (plan: Partial<Plan>) => void;
    onDeletePlan: (id: string) => void;
}

const PlansTab: React.FC<PlansTabProps> = ({ plans, onSavePlan, onDeletePlan }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editingPlan, setEditingPlan] = useState<Partial<Plan>>({});

    const handleEdit = (plan?: Plan) => {
        setEditingPlan(plan || { title: '', price: 0, features: [], color: '#3B82F6' });
        setIsEditing(true);
    };

    const handleSave = () => {
        if (!editingPlan.title || !editingPlan.price) return;
        onSavePlan(editingPlan);
        setIsEditing(false);
        setEditingPlan({});
    };

    if (isEditing) {
        return (
            <div className='bg-white p-6 rounded-2xl shadow-sm border max-w-2xl mx-auto'>
                <h3 className='font-bold text-lg mb-6'>{editingPlan.id ? 'ویرایش پلن' : 'ایجاد پلن جدید'}</h3>
                <div className='space-y-4'>
                    <input
                        placeholder='عنوان پلن'
                        value={editingPlan.title}
                        onChange={e => setEditingPlan({ ...editingPlan, title: e.target.value })}
                        className='w-full border rounded-xl px-4 py-2'
                    />
                    <input
                        placeholder='قیمت (تومان)'
                        value={editingPlan.price ? Number(editingPlan.price).toLocaleString() : ''}
                        onChange={e => {
                            const val = e.target.value.replace(/,/g, '');
                            if (!isNaN(Number(val))) setEditingPlan({ ...editingPlan, price: Number(val) });
                        }}
                        className='w-full border rounded-xl px-4 py-2 dir-ltr text-left'
                    />
                    <textarea
                        placeholder='ویژگی‌ها (هر خط یک ویژگی)'
                        value={editingPlan.features?.join('\n')}
                        onChange={e => setEditingPlan({ ...editingPlan, features: e.target.value.split('\n') })}
                        className='w-full border rounded-xl px-4 py-2 h-32'
                    />
                    <div className='flex justify-end gap-3 mt-6'>
                        <button onClick={() => setIsEditing(false)} className='px-6 py-2 text-gray-600 hover:bg-gray-100 rounded-xl'>انصراف</button>
                        <button onClick={handleSave} className='px-6 py-2 bg-blue-600 text-white rounded-xl'>ذخیره</button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className='space-y-6'>
            <div className='flex justify-between items-center'>
                <h3 className='font-bold text-lg'>مدیریت پلن‌های اشتراک</h3>
                <button onClick={() => handleEdit()} className='flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl'>
                    <Plus size={18} /> پلن جدید
                </button>
            </div>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                {plans.map(plan => (
                    <div key={plan.id} className='bg-white p-6 rounded-2xl shadow-sm border relative group'>
                        <div className='absolute top-4 left-4 flex gap-2 opacity-0 group-hover:opacity-100 transition'>
                            <button onClick={() => handleEdit(plan)} className='p-2 bg-blue-50 text-blue-600 rounded-lg'><Edit size={16} /></button>
                            <button onClick={() => onDeletePlan(plan.id)} className='p-2 bg-red-50 text-red-600 rounded-lg'><Trash2 size={16} /></button>
                        </div>
                        <h3 className='text-xl font-bold text-center mb-2'>{plan.title}</h3>
                        <p className='text-center text-2xl font-bold text-blue-600 mb-4'>{Number(plan.price).toLocaleString('fa-IR')} تومان</p>
                        <div className='space-y-2 border-t pt-4'>
                            {(plan.features || []).map((f, i) => (
                                <div key={i} className='flex items-center gap-2 text-sm text-gray-600'><Check size={16} className='text-green-500' />{f}</div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PlansTab;