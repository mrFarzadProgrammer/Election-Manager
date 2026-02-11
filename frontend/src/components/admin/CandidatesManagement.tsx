import React, { useState } from 'react';
import { CandidateData, Plan } from '../../types';
import { Search, Plus, ChevronLeft, ChevronRight, Bot, X, Key, Edit, CreditCard } from 'lucide-react';
import { api } from '../../services/api';

interface CandidatesManagementProps {
    candidates: CandidateData[];
    plans: Plan[];
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    onEdit: (id: string, data: any) => Promise<void>;
    onDelete: (id: string) => void;
    onToggleStatus: (id: string, currentStatus: boolean) => void;
    onAdd: (data: any) => Promise<void>;
    onResetPassword: (id: string, password: string) => Promise<void>;
    onAssignPlan: (candidateId: string, planId: string) => Promise<void>;
}

const CandidatesManagement: React.FC<CandidatesManagementProps> = ({
    candidates,
    plans,
    searchQuery,
    setSearchQuery,
    onEdit,
    onDelete,
    onToggleStatus,
    onAdd,
    onResetPassword,
    onAssignPlan
}) => {
    const [currentPage, setCurrentPage] = useState(1);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [isSubscriptionModalOpen, setIsSubscriptionModalOpen] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [resetPasswordId, setResetPasswordId] = useState<string | null>(null);
    const [subscriptionCandidateId, setSubscriptionCandidateId] = useState<string | null>(null);
    const [selectedPlanId, setSelectedPlanId] = useState<string>('');
    const [newPassword, setNewPassword] = useState('');

    const [formData, setFormData] = useState({
        name: '',
        username: '',
        password: '',
        bot_name: '',
        bot_token: '',
        phone: '',
        city: '',
        province: '',
        constituency: ''
    });

    const itemsPerPage = 10;

    // Filter candidates
    const filteredCandidates = candidates.filter(c => {
        const query = searchQuery.toLowerCase();
        const statusText = c.is_active ? 'فعال' : 'غیرفعال';

        return (
            (c.full_name || '').toLowerCase().includes(query) ||
            (c.username || '').toLowerCase().includes(query) ||
            (c.bot_name || '').toLowerCase().includes(query) ||
            (c.province || '').toLowerCase().includes(query) ||
            (c.city || '').toLowerCase().includes(query) ||
            (c.constituency || '').toLowerCase().includes(query) ||
            statusText.includes(query)
        );
    });

    // Pagination logic
    const totalPages = Math.ceil(filteredCandidates.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredCandidates.length);
    const currentCandidates = filteredCandidates.slice(startIndex, endIndex);

    const handlePageChange = (page: number) => {
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
        }
    };

    const openAddModal = () => {
        setEditingId(null);
        setFormData({
            name: '',
            username: '',
            password: '',
            bot_name: '',
            bot_token: '',
            phone: '',
            city: '',
            province: '',
            constituency: ''
        });
        setIsModalOpen(true);
    };

    const openEditModal = (candidate: CandidateData) => {
        setEditingId(candidate.id);
        setFormData({
            name: candidate.full_name || '',
            username: candidate.username || '',
            password: '', // Password not shown
            bot_name: candidate.bot_name || '',
            bot_token: candidate.bot_token || '',
            phone: candidate.phone || '',
            city: candidate.city || '',
            province: candidate.province || '',
            constituency: candidate.constituency || ''
        });
        setIsModalOpen(true);
    };

    const openPasswordModal = (id: string) => {
        setResetPasswordId(id);
        setNewPassword('');
        setIsPasswordModalOpen(true);
    };

    const openSubscriptionModal = (id: string) => {
        setSubscriptionCandidateId(id);
        setSelectedPlanId('');
        setIsSubscriptionModalOpen(true);
    };

    const handleSubscriptionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!subscriptionCandidateId || !selectedPlanId) return;

        setIsSubmitting(true);
        try {
            await onAssignPlan(subscriptionCandidateId, selectedPlanId);
            alert('پلن با موفقیت فعال شد');
            setIsSubscriptionModalOpen(false);
        } catch (error: any) {
            console.error(error);
            alert(error.message || 'خطا در فعال‌سازی پلن');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            if (editingId) {
                const { password, ...updateData } = formData; // Don't send empty password on edit unless intended
                await onEdit(editingId, updateData);
            } else {
                await onAdd(formData);
            }
            setIsModalOpen(false);
        } catch (error: any) {
            console.error(error);
            alert(error.message || 'خطا در عملیات');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handlePasswordSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!resetPasswordId) return;
        setIsSubmitting(true);
        try {
            await onResetPassword(resetPasswordId, newPassword);
            setIsPasswordModalOpen(false);
            alert('رمز عبور با موفقیت تغییر کرد');
        } catch (error: any) {
            console.error(error);
            alert(error.message || 'خطا در تغییر رمز عبور');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden animate-fade-in">
                {/* Header & Toolbar */}
                <div className="p-6 border-b border-gray-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h3 className="font-bold text-lg text-gray-800">لیست کاندیداها</h3>
                    <div className="flex items-center gap-3 w-full md:w-auto">
                        <div className="relative flex-1 md:w-64">
                            <Search className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                            <input
                                type="text"
                                placeholder="جستجو..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-10 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition outline-none text-sm"
                            />
                        </div>
                        <button
                            onClick={openAddModal}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl flex items-center gap-2 transition-colors shadow-lg shadow-blue-600/20 whitespace-nowrap"
                        >
                            <Plus size={20} />
                            <span className="font-medium">افزودن</span>
                        </button>
                    </div>
                </div>

                {/* Table */}
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50/50 text-gray-500 text-xs font-medium">
                            <tr>
                                <th className="px-6 py-4 text-right w-16">#</th>
                                <th className="px-6 py-4 text-right">نام کاندید</th>
                                <th className="px-6 py-4 text-right">اطلاعات بات</th>
                                <th className="px-6 py-4 text-right">معرفی صوتی</th>
                                <th className="px-6 py-4 text-right">موقعیت</th>
                                <th className="px-6 py-4 text-right">پلن فعال</th>
                                <th className="px-6 py-4 text-center">وضعیت</th>
                                <th className="px-6 py-4 text-center">عملیات</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {currentCandidates.map((candidate, index) => (
                                <tr key={candidate.id} className="hover:bg-gray-50/80 transition-colors group">
                                    {/* Row Number */}
                                    <td className="px-6 py-4 text-gray-400 text-xs font-mono">
                                        {(currentPage - 1) * itemsPerPage + index + 1}
                                    </td>

                                    {/* Name Column */}
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="font-bold text-gray-800 text-sm mb-1">{candidate.full_name || 'نامشخص'}</span>
                                            <span className="text-xs text-gray-400 dir-ltr text-right font-mono">@{candidate.username}</span>
                                        </div>
                                    </td>

                                    {/* Bot Info Column */}
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col items-start gap-1">
                                            {candidate.bot_name ? (
                                                <>
                                                    <a href={`https://t.me/${candidate.bot_name}`} target="_blank" rel="noreferrer" className="text-blue-600 text-xs font-medium hover:underline dir-ltr flex items-center gap-1">
                                                        @{candidate.bot_name} <Bot size={12} />
                                                    </a>
                                                    <span className="bg-gray-100 text-gray-500 text-[10px] px-2 py-0.5 rounded-md font-mono dir-ltr max-w-[100px] truncate">
                                                        Token: {candidate.bot_token ? `${candidate.bot_token.substring(0, 8)}...` : '-'}
                                                    </span>
                                                </>
                                            ) : (
                                                <span className="text-gray-400 text-xs">-</span>
                                            )}
                                        </div>
                                    </td>

                                    {/* Voice Intro (MVP: exists + duration only) */}
                                    <td className="px-6 py-4">
                                        {candidate.voice_url ? (
                                            <div className="flex flex-col items-start gap-1">
                                                <span className="text-xs font-bold text-green-700 bg-green-50 px-2 py-1 rounded-lg">دارد</span>
                                                {typeof (candidate as any)?.bot_config?.voice_intro_duration === 'number' && (
                                                    <span className="text-[10px] text-gray-500">مدت: {(candidate as any).bot_config.voice_intro_duration}s</span>
                                                )}
                                            </div>
                                        ) : (
                                            <span className="text-xs font-bold text-gray-500 bg-gray-50 px-2 py-1 rounded-lg">ندارد</span>
                                        )}
                                    </td>

                                    {/* Location Column */}
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-1 text-gray-500 text-xs">
                                            {candidate.constituency || candidate.city || candidate.province ? (
                                                <>
                                                    {candidate.constituency ? (
                                                        <span>{candidate.constituency}</span>
                                                    ) : (
                                                        <>
                                                            <span>{candidate.city}</span>
                                                            {candidate.city && candidate.province && <span>، </span>}
                                                            <span>{candidate.province}</span>
                                                        </>
                                                    )}
                                                </>
                                            ) : (
                                                <span className="text-gray-400">-</span>
                                            )}
                                        </div>
                                    </td>

                                    {/* Active Plan Column */}
                                    <td className="px-6 py-4">
                                        {(() => {
                                            const activePlan = plans.find(p => p.id === candidate.active_plan_id);
                                            return activePlan ? (
                                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: activePlan.color + '20', color: activePlan.color }}>
                                                    {activePlan.title}
                                                </span>
                                            ) : (
                                                <span className="text-gray-400 text-xs">-</span>
                                            );
                                        })()}
                                    </td>

                                    {/* Status Column */}
                                    < td className="px-6 py-4 text-center" >
                                        <button
                                            onClick={() => onToggleStatus(candidate.id, candidate.is_active || false)}
                                            className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${candidate.is_active
                                                ? 'bg-green-50 text-green-600 border border-green-100 hover:bg-green-100'
                                                : 'bg-red-50 text-red-600 border border-red-100 hover:bg-red-100'
                                                }`}
                                        >
                                            {candidate.is_active ? 'فعال' : 'غیرفعال'}
                                        </button>
                                    </td>

                                    {/* Actions Column */}
                                    <td className="px-6 py-4 text-center">
                                        <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button onClick={() => openSubscriptionModal(candidate.id)} className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition" title="مدیریت اشتراک">
                                                <CreditCard size={16} />
                                            </button>
                                            <button onClick={() => openPasswordModal(candidate.id)} className="p-2 text-gray-500 hover:text-yellow-600 hover:bg-yellow-50 rounded-lg transition" title="تغییر رمز عبور">
                                                <Key size={16} />
                                            </button>
                                            <button onClick={() => openEditModal(candidate)} className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition" title="ویرایش">
                                                <Edit size={16} />
                                            </button>
                                            <button onClick={() => onDelete(candidate.id)} className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition" title="حذف">
                                                <X size={16} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {currentCandidates.length === 0 && (
                                <tr>
                                    <td colSpan={7} className="px-6 py-8 text-center text-gray-400 text-sm">
                                        هیچ کاندیدایی یافت نشد.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div >

                {/* Pagination */}
                < div className="p-4 border-t border-gray-100 flex items-center justify-between bg-gray-50/30" >
                    <div className="text-xs text-gray-500 font-medium">
                        نمایش {filteredCandidates.length > 0 ? startIndex + 1 : 0} تا {endIndex} از {filteredCandidates.length}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => handlePageChange(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="p-2 bg-white border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                            <ChevronLeft size={16} />
                        </button>
                        <div className="flex items-center gap-1">
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                                <button
                                    key={page}
                                    onClick={() => handlePageChange(page)}
                                    className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-medium transition ${currentPage === page
                                        ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                                        : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                                        }`}
                                >
                                    {page}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="p-2 bg-white border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                            <ChevronRight size={16} />
                        </button>
                    </div>
                </div >
            </div >

            {/* Add/Edit Candidate Modal */}
            {
                isModalOpen && (
                    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in">
                        <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden animate-fade-in-up">
                            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                                <h3 className="font-bold text-lg text-gray-800">{editingId ? 'ویرایش کاندیدا' : 'افزودن کاندیدای جدید'}</h3>
                                <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600 transition">
                                    <X size={24} />
                                </button>
                            </div>
                            <form onSubmit={handleSubmit} className="p-6 space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">نام و نام خانوادگی <span className="text-red-500">*</span></label>
                                        <input
                                            required
                                            type="text"
                                            value={formData.name}
                                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition"
                                            placeholder="مثال: دکتر محمدی"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">نام کاربری <span className="text-red-500">*</span></label>
                                        <input
                                            required
                                            type="text"
                                            value={formData.username}
                                            onChange={e => setFormData({ ...formData, username: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                            placeholder="username"
                                            disabled={!!editingId} // Username usually not editable
                                        />
                                    </div>
                                    {!editingId && (
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-gray-700">رمز عبور <span className="text-red-500">*</span></label>
                                            <input
                                                required
                                                type="password"
                                                value={formData.password}
                                                onChange={e => setFormData({ ...formData, password: e.target.value })}
                                                className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                                placeholder="********"
                                            />
                                        </div>
                                    )}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">شماره تماس</label>
                                        <input
                                            type="text"
                                            value={formData.phone}
                                            onChange={e => setFormData({ ...formData, phone: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                            placeholder="0912..."
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">نام ربات <span className="text-red-500">*</span></label>
                                        <input
                                            required
                                            type="text"
                                            value={formData.bot_name}
                                            onChange={e => setFormData({ ...formData, bot_name: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                            placeholder="MyBot"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">توکن ربات <span className="text-red-500">*</span></label>
                                        <input
                                            required
                                            type="text"
                                            value={formData.bot_token}
                                            onChange={e => setFormData({ ...formData, bot_token: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                            placeholder="123456:ABC-DEF..."
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">استان</label>
                                        <input
                                            type="text"
                                            value={formData.province}
                                            onChange={e => setFormData({ ...formData, province: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition"
                                            placeholder="مثال: تهران"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">حوزه انتخابیه</label>
                                        <input
                                            type="text"
                                            value={formData.constituency}
                                            onChange={e => setFormData({ ...formData, constituency: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition"
                                            placeholder="مثال: تهران"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-700">شهر</label>
                                        <input
                                            type="text"
                                            value={formData.city}
                                            onChange={e => setFormData({ ...formData, city: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition"
                                            placeholder="مثال: تهران"
                                        />
                                    </div>
                                </div>
                                <div className="pt-4 flex items-center justify-end gap-3 border-t border-gray-100 mt-4">
                                    <button
                                        type="button"
                                        onClick={() => setIsModalOpen(false)}
                                        className="px-6 py-2.5 rounded-xl text-gray-600 hover:bg-gray-100 transition font-medium"
                                    >
                                        انصراف
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="px-6 py-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition font-medium shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                    >
                                        {isSubmitting ? 'در حال ثبت...' : (editingId ? 'ویرایش کاندیدا' : 'ثبت کاندیدا')}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

            {/* Password Reset Modal */}
            {
                isPasswordModalOpen && (
                    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in">
                        <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-fade-in-up">
                            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                                <h3 className="font-bold text-lg text-gray-800">تغییر رمز عبور</h3>
                                <button onClick={() => setIsPasswordModalOpen(false)} className="text-gray-400 hover:text-gray-600 transition">
                                    <X size={24} />
                                </button>
                            </div>
                            <form onSubmit={handlePasswordSubmit} className="p-6 space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-gray-700">رمز عبور جدید <span className="text-red-500">*</span></label>
                                    <input
                                        required
                                        type="password"
                                        value={newPassword}
                                        onChange={e => setNewPassword(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition dir-ltr text-left"
                                        placeholder="********"
                                    />
                                </div>
                                <div className="pt-4 flex items-center justify-end gap-3 border-t border-gray-100 mt-4">
                                    <button
                                        type="button"
                                        onClick={() => setIsPasswordModalOpen(false)}
                                        className="px-6 py-2.5 rounded-xl text-gray-600 hover:bg-gray-100 transition font-medium"
                                    >
                                        انصراف
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="px-6 py-2.5 rounded-xl bg-yellow-500 text-white hover:bg-yellow-600 transition font-medium shadow-lg shadow-yellow-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                    >
                                        {isSubmitting ? 'در حال ثبت...' : 'تغییر رمز'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }
            {/* Subscription Modal */}
            {
                isSubscriptionModalOpen && (
                    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in">
                        <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-fade-in-up">
                            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                                <h3 className="font-bold text-lg text-gray-800">مدیریت اشتراک</h3>
                                <button onClick={() => setIsSubscriptionModalOpen(false)} className="text-gray-400 hover:text-gray-600 transition">
                                    <X size={24} />
                                </button>
                            </div>
                            <form onSubmit={handleSubscriptionSubmit} className="p-6 space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-gray-700">انتخاب پلن <span className="text-red-500">*</span></label>
                                    <select
                                        required
                                        value={selectedPlanId}
                                        onChange={(e) => setSelectedPlanId(e.target.value)}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition outline-none"
                                    >
                                        <option value="">انتخاب کنید...</option>
                                        {plans.map(plan => (
                                            <option key={plan.id} value={plan.id}>
                                                {plan.title} - {Number(plan.price).toLocaleString('fa-IR')} تومان
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="flex items-center justify-end gap-3 pt-4">
                                    <button
                                        type="button"
                                        onClick={() => setIsSubscriptionModalOpen(false)}
                                        className="px-4 py-2.5 rounded-xl text-gray-500 hover:bg-gray-100 transition font-medium"
                                    >
                                        انصراف
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="px-6 py-2.5 rounded-xl bg-green-600 text-white hover:bg-green-700 transition font-medium shadow-lg shadow-green-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {isSubmitting ? 'در حال ثبت...' : 'فعال‌سازی پلن'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }
        </>
    );
};

export default CandidatesManagement;
