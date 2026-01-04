import React from 'react';
import { CandidateData, Plan, Ticket } from '../../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { Users, UserCheck, Bot, Activity, CreditCard, MessageSquare, DollarSign } from 'lucide-react';

interface DashboardTabProps {
    candidates: CandidateData[];
    plans: Plan[];
    tickets: Ticket[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const DashboardTab: React.FC<DashboardTabProps> = ({ candidates, plans, tickets }) => {
    // Stats Calculations
    const totalCandidates = candidates.length;
    const activeCandidates = candidates.filter(c => c.is_active).length;
    const totalBots = candidates.filter(c => c.bot_token).length;
    const activeBots = candidates.filter(c => c.bot_token && c.is_active).length;

    // Ticket Stats
    const openTickets = tickets.filter(t => t.status === 'OPEN').length;
    const closedTickets = tickets.filter(t => t.status === 'CLOSED').length;
    const answeredTickets = tickets.filter(t => t.status === 'ANSWERED').length;

    // Revenue & Plan Distribution
    let totalRevenue = 0;
    const planCounts: { [key: string]: number } = {};

    candidates.forEach(c => {
        if (c.active_plan_id) {
            const plan = plans.find(p => p.id.toString() === c.active_plan_id?.toString());
            if (plan) {
                // Revenue
                const price = parseInt(plan.price.replace(/,/g, '')) || 0;
                totalRevenue += price;

                // Distribution
                planCounts[plan.title] = (planCounts[plan.title] || 0) + 1;
            }
        }
    });

    const planChartData = Object.keys(planCounts).map(key => ({
        name: key,
        value: planCounts[key]
    }));

    const ticketChartData = [
        { name: 'باز', value: openTickets },
        { name: 'پاسخ داده شده', value: answeredTickets },
        { name: 'بسته شده', value: closedTickets },
    ].filter(d => d.value > 0);

    // User Growth Chart (Mock/Real)
    const [selectedCity, setSelectedCity] = React.useState<string>('all');

    // Extract unique cities
    const cities = Array.from(new Set(candidates.map(c => c.city).filter(Boolean))) as string[];

    // Filter and Sort Candidates
    const topCandidates = candidates
        .filter(c => selectedCity === 'all' || c.city === selectedCity)
        .sort((a, b) => (b.vote_count || 0) - (a.vote_count || 0))
        .slice(0, 10)
        .map(c => ({
            name: c.full_name || c.username || 'نامشخص',
            users: c.vote_count || 0,
            city: c.city
        }));

    return (
        <div className="space-y-6 animate-fade-in pb-10">
            {/* Top Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="کل کاندیداها"
                    value={totalCandidates}
                    icon={<Users className="w-6 h-6 text-blue-600" />}
                    bg="bg-blue-50"
                />
                <StatCard
                    title="درآمد تقریبی (تومان)"
                    value={totalRevenue.toLocaleString()}
                    icon={<DollarSign className="w-6 h-6 text-green-600" />}
                    bg="bg-green-50"
                />
                <StatCard
                    title="تیکت‌های باز"
                    value={openTickets}
                    icon={<MessageSquare className="w-6 h-6 text-orange-600" />}
                    bg="bg-orange-50"
                />
                <StatCard
                    title="بات‌های فعال"
                    value={activeBots}
                    icon={<Bot className="w-6 h-6 text-purple-600" />}
                    bg="bg-purple-50"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Plan Distribution Chart */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                    <h3 className="text-lg font-bold text-gray-700 flex items-center gap-2 mb-6">
                        <CreditCard className="w-5 h-5 text-indigo-500" />
                        توزیع پلن‌های خریداری شده
                    </h3>
                    <div className="h-[300px] w-full" dir="ltr">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={planChartData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {planChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Top Candidates Chart */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-bold text-gray-700 flex items-center gap-2">
                            <Activity className="w-5 h-5 text-green-500" />
                            ۱۰ کاندیدای برتر
                        </h3>
                        <select
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5 outline-none"
                            value={selectedCity}
                            onChange={(e) => setSelectedCity(e.target.value)}
                        >
                            <option value="all">همه شهرها</option>
                            {cities.map(city => (
                                <option key={city} value={city}>{city}</option>
                            ))}
                        </select>
                    </div>

                    <div className="h-[300px] w-full" dir="ltr">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={topCandidates} layout="vertical" margin={{ left: 40 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 12 }} />
                                <Tooltip
                                    cursor={{ fill: 'transparent' }}
                                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                                />
                                <Bar dataKey="users" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20} name="تعداد آرا" />
                            </BarChart>
                        </ResponsiveContainer>
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
