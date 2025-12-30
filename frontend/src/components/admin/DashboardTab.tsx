import React from 'react';
import { CandidateData } from '../../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, UserCheck, Bot, Activity, LayoutDashboard, Quote } from 'lucide-react';

interface DashboardTabProps {
    candidates: CandidateData[];
}

const DashboardTab: React.FC<DashboardTabProps> = ({ candidates }) => {
    // Calculate stats
    const totalCandidates = candidates.length;
    const activeCandidates = candidates.filter(c => c.is_active).length;
    // Assuming bot_token presence indicates a bot is configured
    const totalBots = candidates.filter(c => c.bot_token).length;
    // Assuming bot is active if candidate is active and has token
    const activeBots = candidates.filter(c => c.bot_token && c.is_active).length;

    // Prepare chart data
    // Using vote_count as a proxy for "audience" or "users"
    // If vote_count is not available, we default to 0
    const chartData = candidates.map(c => ({
        name: c.full_name || c.username || 'نامشخص',
        users: c.vote_count || 0
    }));

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Quote Banner */}
            <div className="bg-gradient-to-r from-blue-900 to-blue-700 rounded-2xl p-8 text-white text-center relative overflow-hidden shadow-lg">
                <div className="absolute top-6 left-8 opacity-20">
                    <svg width="100" height="100" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14.017 21L14.017 18C14.017 16.8954 13.1216 16 12.017 16H9.01703C7.91246 16 7.01703 16.8954 7.01703 18L7.01703 21H2.01703V7H16.017V21H14.017ZM18.017 5V21H22.017V5H18.017Z" style={{ display: 'none' }} />
                        <path d="M6 17h3l2-4V7H5v6h3zm8 0h3l2-4V7h-6v6h3z" />
                    </svg>
                </div>
                <div className="relative z-10">
                    <h2 className="text-xl md:text-2xl font-bold mb-4 leading-relaxed">
                        «انتخابات مظهر اقتدار ملی است؛ اگر اقتدار ملی نبود، امنیت ملی هم نخواهد بود.»
                    </h2>
                    <p className="text-blue-200 text-sm">مقام معظم رهبری</p>
                    <div className="absolute top-0 right-0 bg-blue-800/50 px-3 py-1 rounded-full text-xs backdrop-blur-sm border border-blue-400/30">
                        سخن روز
                    </div>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="کل کاندیداها"
                    value={totalCandidates}
                    icon={<Users className="w-6 h-6 text-blue-600" />}
                    bg="bg-blue-50"
                />
                <StatCard
                    title="کاندیدای فعال"
                    value={activeCandidates}
                    icon={<UserCheck className="w-6 h-6 text-green-600" />}
                    bg="bg-green-50"
                />
                <StatCard
                    title="کل بات‌ها"
                    value={totalBots}
                    icon={<Bot className="w-6 h-6 text-purple-600" />}
                    bg="bg-purple-50"
                />
                <StatCard
                    title="بات‌های فعال"
                    value={activeBots}
                    icon={<Activity className="w-6 h-6 text-indigo-600" />}
                    bg="bg-indigo-50"
                />
            </div>

            {/* Chart Section */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold text-gray-700 flex items-center gap-2">
                        <Users className="w-5 h-5 text-blue-500" />
                        آمار جذب مخاطب کاندیداها
                    </h3>
                </div>
                <div className="h-[400px] w-full" dir="ltr">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#6b7280' }} dy={10} />
                            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280' }} />
                            <Tooltip
                                cursor={{ fill: '#f3f4f6' }}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                            />
                            <Bar dataKey="users" name="تعداد کاربر" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

const StatCard = ({ title, value, icon, bg }: { title: string, value: number, icon: React.ReactNode, bg: string }) => (
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
