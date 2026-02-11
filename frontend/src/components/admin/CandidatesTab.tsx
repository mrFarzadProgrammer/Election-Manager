import React from 'react';
import { CandidateData } from '../../types';
import { Search, Edit, Trash2, Bot } from 'lucide-react';

interface CandidatesTabProps {
    candidates: CandidateData[];
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    onEdit: (candidate: CandidateData) => void;
    onDelete: (id: string) => void;
    onToggleStatus: (id: string, currentStatus: boolean) => void;
}

const CandidatesTab: React.FC<CandidatesTabProps> = ({
    candidates,
    searchQuery,
    setSearchQuery,
    onEdit,
    onDelete,
    onToggleStatus
}) => {
    const filteredCandidates = candidates.filter(c =>
        (c.name || '').includes(searchQuery) || (c.username || '').includes(searchQuery)
    );

    return (
        <div className='bg-white rounded-2xl shadow-sm border overflow-hidden'>
            <div className='p-6 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-4'>
                <h3 className='font-bold text-lg'>لیست کاندیداها</h3>
                <div className='relative w-full sm:w-64'>
                    <Search className='absolute right-3 top-3 text-gray-400' size={18} />
                    <input
                        type='text'
                        placeholder='جستجو...'
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className='w-full pl-4 pr-10 py-2 bg-gray-50 border rounded-xl focus:bg-white transition outline-none'
                    />
                </div>
            </div>

            <div className='overflow-x-auto'>
                <table className='w-full'>
                    <thead className='bg-gray-50 text-gray-500 text-sm'>
                        <tr>
                            <th className='p-4 text-right'>نام کاندیدا</th>
                            <th className='p-4 text-right'>نام کاربری</th>
                            <th className='p-4 text-right'>وضعیت ربات</th>
                            <th className='p-4 text-center'>وضعیت حساب</th>
                            <th className='p-4 text-center'>عملیات</th>
                        </tr>
                    </thead>
                    <tbody className='divide-y'>
                        {filteredCandidates.map(candidate => (
                            <tr key={candidate.id} className='hover:bg-gray-50 transition'>
                                <td className='p-4 font-medium'>{candidate.name}</td>
                                <td className='p-4 text-gray-600 dir-ltr text-right'>{candidate.username}</td>
                                <td className='p-4'>
                                    {candidate.bot_name ? (
                                        <span className='flex items-center gap-1 text-blue-600 text-sm bg-blue-50 px-2 py-1 rounded-lg w-fit'>
                                            <Bot size={14} /> @{candidate.bot_name}
                                        </span>
                                    ) : (
                                        <span className='text-gray-400 text-sm'>-</span>
                                    )}
                                </td>
                                <td className='p-4 text-center'>
                                    <button
                                        onClick={() => onToggleStatus(candidate.id, candidate.is_active || false)}
                                        className={`px-3 py-1 rounded-full text-xs font-bold transition ${candidate.is_active
                                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                            : 'bg-red-100 text-red-700 hover:bg-red-200'
                                            }`}
                                    >
                                        {candidate.is_active ? 'فعال' : 'غیرفعال'}
                                    </button>
                                </td>
                                <td className='p-4'>
                                    <div className='flex items-center justify-center gap-2'>
                                        <button onClick={() => onEdit(candidate)} className='p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition'>
                                            <Edit size={18} />
                                        </button>
                                        <button onClick={() => onDelete(candidate.id)} className='p-2 text-red-600 hover:bg-red-50 rounded-lg transition'>
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default CandidatesTab;