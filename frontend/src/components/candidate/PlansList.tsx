import React from 'react';
import { Plan } from '../../types';
import { Check } from 'lucide-react';

interface PlansListProps {
    plans: Plan[];
    onSelectPlan: (plan: Plan) => void;
}

const PlansList: React.FC<PlansListProps> = ({ plans, onSelectPlan }) => {
    return (
        <div className="space-y-8 p-4 md:p-0">
            {/* Header Banner */}
            <div className="bg-blue-600 rounded-2xl p-8 text-white text-center relative overflow-hidden shadow-lg shadow-blue-200">
                <div className="relative z-10">
                    <h2 className="text-2xl font-bold mb-3">طرح‌های عضویت و اشتراک</h2>
                    <p className="text-blue-100 text-sm md:text-base">با ارتقای پنل خود، به امکانات ویژه‌ای مثل بات اختصاصی و مدیریت هوشمند گروه دسترسی پیدا کنید.</p>
                </div>
            </div>

            {/* Plans Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {plans.map((plan) => (
                    <div key={plan.id} className="bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 hover:shadow-xl transition-all duration-300 flex flex-col group">
                        {/* Card Header with Color */}
                        <div
                            className="p-8 text-center text-white relative"
                            style={{ backgroundColor: plan.color || '#3b82f6' }}
                        >
                            <div className="inline-block bg-white/20 backdrop-blur-md rounded-full px-4 py-1 text-xs font-medium mb-4 border border-white/30">
                                پیشنهاد ادمین
                            </div>
                            <h3 className="text-2xl font-bold mb-2">{plan.title}</h3>
                        </div>

                        {/* Price Section */}
                        <div className="p-6 text-center border-b border-gray-50">
                            <div className="text-3xl font-black text-gray-800 mb-1 flex items-center justify-center gap-2">
                                {Number(plan.price).toLocaleString('fa-IR')} <span className="text-sm font-medium text-gray-500 mt-2">تومان</span>
                            </div>
                            <div className="text-xs text-gray-400 font-medium">ماهانه</div>
                        </div>

                        {/* Features */}
                        <div className="p-6 flex-grow">
                            <ul className="space-y-4">
                                {(plan.features || []).map((feature, idx) => (
                                    <li key={idx} className="flex items-center gap-3 text-sm text-gray-600 font-medium">
                                        <div className="w-5 h-5 rounded-full bg-green-50 flex items-center justify-center shrink-0">
                                            <Check className="w-3.5 h-3.5 text-green-500" strokeWidth={3} />
                                        </div>
                                        <span>{feature}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Action Button */}
                        <div className="p-6 pt-0">
                            <button
                                onClick={() => onSelectPlan(plan)}
                                className="w-full py-3.5 rounded-xl border-2 border-blue-600 text-blue-600 font-bold hover:bg-blue-600 hover:text-white transition-all duration-300 shadow-sm hover:shadow-blue-200"
                            >
                                خرید اشتراک
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PlansList;
