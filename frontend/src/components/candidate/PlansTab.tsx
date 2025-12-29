import React from 'react';
import { Plan } from '../../types';
import { Check } from 'lucide-react';

interface PlansTabProps {
    plans: Plan[];
    onSelectPlan: (plan: Plan) => void;
}

const PlansTab: React.FC<PlansTabProps> = ({ plans, onSelectPlan }) => {
    return (
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
            {plans.map(plan => (
                <div key={plan.id} className='bg-white p-6 rounded-2xl shadow-sm border hover:shadow-md transition'>
                    <h3 className='text-xl font-bold text-center mb-2'>{plan.title}</h3>
                    <p className='text-center text-2xl font-bold text-blue-600 mb-4'>{Number(plan.price).toLocaleString('fa-IR')} تومان</p>
                    <div className='space-y-2 mb-6'>
                        {(plan.features || []).map((f, i) => (
                            <div key={i} className='flex items-center gap-2 text-sm text-gray-600'><Check size={16} className='text-green-500' />{f}</div>
                        ))}
                    </div>
                    <button onClick={() => onSelectPlan(plan)} className='w-full py-2 bg-blue-600 text-white rounded-xl'>خرید اشتراک</button>
                </div>
            ))}
        </div>
    );
};

export default PlansTab;