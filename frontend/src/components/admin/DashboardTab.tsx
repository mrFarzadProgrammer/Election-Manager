import React, { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { CandidateData, Plan, Ticket, AdminDashboardStats } from '../../types';
import { Bot, HelpCircle, MessageSquare, Wrench } from 'lucide-react';

interface DashboardTabProps {
    candidates: CandidateData[];
    plans: Plan[];
    tickets: Ticket[];
    onTabChange: (tab: 'DASHBOARD' | 'CANDIDATES' | 'PLANS' | 'TICKETS' | 'ANNOUNCEMENTS' | 'BOT_REQUESTS') => void;
}

const DashboardTab: React.FC<DashboardTabProps> = ({ candidates, plans, tickets, onTabChange }) => {
    const [stats, setStats] = useState<AdminDashboardStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const run = async () => {
            const token = localStorage.getItem('access_token') || '';

            setLoading(true);
            setError(null);
            try {
                const data = await api.getAdminDashboardStats(token);
                setStats(data);
            } catch (e: any) {
                setError(e?.message || 'خطا در دریافت اطلاعات داشبورد');
            } finally {
                setLoading(false);
            }
        };

        run();
    }, []);

    const valueOrDash = (v: number | undefined) => (typeof v === 'number' && Number.isFinite(v) ? v : '—');

    return (
        <div className="space-y-4 pb-10">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <h3 className="text-lg font-bold text-gray-700">داشبورد</h3>
                <p className="text-xs text-gray-400 mt-1">نسخه MVP (عملیاتی)</p>

                {error && (
                    <div className="mt-4 bg-red-50 border border-red-100 text-red-700 rounded-xl p-3 text-sm">
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
                    <StatCard
                        title="تعداد بات‌های فعال"
                        value={loading ? '...' : valueOrDash(stats?.active_bots)}
                        icon={<Bot className="w-6 h-6 text-blue-600" />}
                        bg="bg-blue-50"
                    />
                    <StatCard
                        title="تعداد کل سؤال‌ها"
                        value={loading ? '...' : valueOrDash(stats?.total_questions)}
                        icon={<HelpCircle className="w-6 h-6 text-indigo-600" />}
                        bg="bg-indigo-50"
                    />
                    <StatCard
                        title="تعداد کل نظرها"
                        value={loading ? '...' : valueOrDash(stats?.total_feedback)}
                        icon={<MessageSquare className="w-6 h-6 text-orange-600" />}
                        bg="bg-orange-50"
                    />
                    <div onClick={() => onTabChange('BOT_REQUESTS')} className="cursor-pointer">
                        <StatCard
                            title="تعداد درخواست ساخت بات"
                            value={loading ? '...' : valueOrDash(stats?.total_bot_requests)}
                            icon={<Wrench className="w-6 h-6 text-green-600" />}
                            bg="bg-green-50"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

const StatCard = ({ title, value, icon, bg }: { title: string, value: string | number, icon: React.ReactNode, bg: string }) => (
    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between hover:shadow-md transition-shadow">
        <div className="text-right">
            <p className="text-gray-500 text-sm mb-1">{title}</p>
            <p className="text-2xl font-bold text-gray-800">{value}</p>
        </div>
        <div className={`p-3 rounded-xl ${bg}`}>
            {icon}
        </div>
    </div>
);

export default DashboardTab;
