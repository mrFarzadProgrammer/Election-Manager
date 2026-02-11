import React from 'react';
import { Lock } from 'lucide-react';

interface LockedFeatureNoticeProps {
    title?: string;
    message?: string;
}

const LockedFeatureNotice: React.FC<LockedFeatureNoticeProps> = ({
    title = 'این بخش در نسخه فعلی غیرفعال است',
    message = 'برای فعال‌سازی این قسمت، با مدیر سیستم هماهنگ کنید.'
}) => {
    return (
        <div className="bg-white rounded-2xl shadow-sm border p-6">
            <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600">
                    <Lock size={18} />
                </div>
                <div>
                    <h3 className="text-sm font-bold text-gray-800">{title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{message}</p>
                </div>
            </div>
        </div>
    );
};

export default LockedFeatureNotice;
