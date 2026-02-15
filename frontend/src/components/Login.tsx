import React, { useState } from 'react';
import { api } from '../services/api';
import { LEGACY_TOKEN_STORAGE_ENABLED } from '../services/api';
import { Vote, User as UserIcon, Lock, ArrowRight } from 'lucide-react';
import QuotesCarousel from './QuotesCarousel';

interface LoginProps {
    onLogin: (user: any) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const tokens = await api.login(username, password);

            // Prefer cookie-based session (HttpOnly tokens) first.
            // If cookies aren't available (dev proxy / browser policy), fall back to legacy
            // token-in-storage to avoid immediate "session expired" errors.
            try {
                const user = await api.getMe('');
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                onLogin(user);
                return;
            } catch {
                // Cookie session didn't work.
            }

            if (!LEGACY_TOKEN_STORAGE_ENABLED) {
                throw new Error('ورود امن با کوکی انجام نشد. لطفاً تنظیمات کوکی/مرورگر را بررسی کنید.');
            }

            if (tokens?.access_token) localStorage.setItem('access_token', tokens.access_token);
            if (tokens?.refresh_token) localStorage.setItem('refresh_token', tokens.refresh_token);

            const user = await api.getMe(tokens?.access_token || '');
            onLogin(user);
        } catch (err: any) {
            setError(err.message || "خطا در ورود به سیستم");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex bg-gray-50">
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white shadow-2xl z-10 relative">
                <div className="w-full max-w-md space-y-8 animate-fade-in-up">
                    <div className="text-center space-y-2">
                        <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-lg shadow-blue-500/30 transform rotate-3">
                            <Vote size={32} className="text-white" />
                        </div>
                        <h1 className="text-3xl font-extrabold text-gray-800 tracking-tight">
                            سامانه جامع انتخابات
                        </h1>
                        <p className="text-gray-500">خوش آمدید! لطفا جهت دسترسی وارد شوید.</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-6 mt-8">
                        <div className="space-y-1">
                            <label className="text-sm font-semibold text-gray-700 mr-1">
                                نام کاربری
                            </label>
                            <div className="relative">
                                <UserIcon
                                    className="absolute right-3 top-3.5 text-gray-400"
                                    size={20}
                                />
                                <input
                                    type="text"
                                    className="w-full pr-10 pl-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition duration-200"
                                    placeholder="نام کاربری خود را وارد کنید"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    disabled={loading}
                                />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <label className="text-sm font-semibold text-gray-700 mr-1">
                                رمز عبور
                            </label>
                            <div className="relative">
                                <Lock className="absolute right-3 top-3.5 text-gray-400" size={20} />
                                <input
                                    type="password"
                                    className="w-full pr-10 pl-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition duration-200"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    disabled={loading}
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg flex items-center gap-2">
                                <span className="w-1.5 h-1.5 bg-red-600 rounded-full"></span>
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-500/30 transition duration-300 flex items-center justify-center gap-2 group"
                        >
                            {loading ? "در حال ورود..." : "ورود به سامانه"}
                            <ArrowRight
                                size={20}
                                className="group-hover:-translate-x-1 transition-transform"
                            />
                        </button>
                    </form>

                    {(() => {
                        try {
                            return (import.meta as any)?.env?.DEV;
                        } catch {
                            return false;
                        }
                    })() && (
                            <div className="mt-8 p-6 border border-dashed border-gray-300 rounded-xl bg-gray-50/50">
                                <div className="text-center text-sm text-gray-500">
                                    <p className="font-medium text-gray-700 mb-2">داده‌های تست</p>
                                    <div className="grid grid-cols-1 gap-2">
                                        <div className="bg-white p-2 rounded border border-gray-200">
                                            <span className="block font-bold text-blue-600">مدیر کل</span>
                                            <code className="text-xs">admin / admin123</code>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                </div>
            </div>

            <div className="hidden lg:flex w-1/2 relative overflow-hidden p-0">
                <QuotesCarousel />
            </div>
        </div>
    );
};

export default Login;
