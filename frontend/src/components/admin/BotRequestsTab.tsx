import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import { BotRequestSubmission, BotRequestStatus } from '../../types';

const statusLabel = (s: BotRequestStatus) => {
    const v = String(s || '').toLowerCase();
    if (v === 'new_request') return 'جدید';
    if (v === 'in_progress') return 'در حال پیگیری';
    if (v === 'done') return 'انجام شد';
    return String(s || '-');
};

const BotRequestsTab: React.FC = () => {
    const [items, setItems] = useState<BotRequestSubmission[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [filterStatus, setFilterStatus] = useState<string>('');

    const getToken = () => localStorage.getItem('access_token') || '';

    const load = async () => {
        const token = getToken();
        if (!token) return;
        setIsLoading(true);
        try {
            const rows = await api.getBotRequests(token, filterStatus || undefined);
            setItems(rows);
        } catch (e: any) {
            console.error(e);
            alert(e?.message || 'خطا در دریافت درخواست‌ها');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filterStatus]);

    const handleStatusChange = async (id: string, next: string) => {
        const token = getToken();
        if (!token) return;
        const prev = items;
        setItems(prevItems => prevItems.map(it => it.id === id ? { ...it, status: next } : it));
        try {
            await api.updateBotRequestStatus(id, next, token);
        } catch (e: any) {
            console.error(e);
            setItems(prev);
            alert(e?.message || 'خطا در بروزرسانی وضعیت');
        }
    };

    return (
        <div className='bg-white rounded-2xl shadow-sm border overflow-hidden'>
            <div className='p-6 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-4'>
                <div>
                    <h3 className='font-bold text-lg'>درخواست‌های ساخت بات</h3>
                    <p className='text-xs text-gray-500 mt-1'>لیست درخواست‌های ثبت‌شده از داخل بات‌ها</p>
                </div>

                <div className='flex items-center gap-2'>
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className='px-3 py-2 bg-gray-50 border rounded-xl outline-none'
                    >
                        <option value=''>همه</option>
                        <option value='new_request'>جدید</option>
                        <option value='in_progress'>در حال پیگیری</option>
                        <option value='done'>انجام شد</option>
                    </select>
                    <button
                        onClick={load}
                        className='px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-bold'
                        disabled={isLoading}
                    >
                        {isLoading ? 'در حال دریافت…' : 'بروزرسانی'}
                    </button>
                </div>
            </div>

            <div className='overflow-x-auto'>
                <table className='w-full'>
                    <thead className='bg-gray-50 text-gray-500 text-sm'>
                        <tr>
                            <th className='p-4 text-right'>نام</th>
                            <th className='p-4 text-right'>نقش</th>
                            <th className='p-4 text-right'>حوزه</th>
                            <th className='p-4 text-right'>تماس</th>
                            <th className='p-4 text-right'>یوزرنیم</th>
                            <th className='p-4 text-right'>وضعیت</th>
                            <th className='p-4 text-right'>متن</th>
                        </tr>
                    </thead>
                    <tbody className='divide-y'>
                        {items.map(it => (
                            <tr key={it.id} className='hover:bg-gray-50 transition align-top'>
                                <td className='p-4 font-medium whitespace-nowrap'>{it.requester_full_name || '-'}</td>
                                <td className='p-4 whitespace-nowrap'>{it.role || '-'}</td>
                                <td className='p-4 whitespace-nowrap'>{it.constituency || '-'}</td>
                                <td className='p-4 whitespace-nowrap dir-ltr text-right'>{it.requester_contact || '-'}</td>
                                <td className='p-4 whitespace-nowrap dir-ltr text-right'>{it.telegram_username ? `@${it.telegram_username}` : '-'}</td>
                                <td className='p-4 whitespace-nowrap'>
                                    <select
                                        value={String(it.status || '')}
                                        onChange={(e) => handleStatusChange(it.id, e.target.value)}
                                        className='px-3 py-2 bg-gray-50 border rounded-xl outline-none'
                                    >
                                        <option value='new_request'>جدید</option>
                                        <option value='in_progress'>در حال پیگیری</option>
                                        <option value='done'>انجام شد</option>
                                    </select>
                                    <div className='text-[11px] text-gray-500 mt-1'>{statusLabel(it.status)}</div>
                                </td>
                                <td className='p-4 text-gray-700 text-sm whitespace-pre-wrap min-w-[280px]'>{it.text || '-'}</td>
                            </tr>
                        ))}

                        {!items.length && (
                            <tr>
                                <td className='p-6 text-center text-gray-400' colSpan={7}>
                                    موردی یافت نشد.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default BotRequestsTab;
