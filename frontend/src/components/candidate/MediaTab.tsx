import React, { useEffect, useState, useRef } from 'react';
import { CandidateData } from '../../types';
import { Save, Bot, Mic, Image as ImageIcon, Upload } from 'lucide-react';
import BotPreview from '../BotPreview';
import { api } from '../../services/api';

interface MediaTabProps {
    candidate: CandidateData;
    onUpdate: (updatedData: Partial<CandidateData>) => Promise<void>;
}

const MediaTab: React.FC<MediaTabProps> = ({ candidate, onUpdate }) => {
    const [formData, setFormData] = useState<CandidateData>(candidate);
    const [previewImage, setPreviewImage] = useState<string | null>(candidate.image_url || null);
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [voiceFile, setVoiceFile] = useState<File | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const voiceInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        setFormData(candidate);
        setPreviewImage(candidate.image_url || null);
    }, [candidate]);

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setImageFile(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setPreviewImage(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const handleVoiceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setVoiceFile(file);
        }
    };

    const handleSave = async () => {
        const token = localStorage.getItem('access_token') || '';

        setIsSaving(true);
        try {
            let image_url = formData.image_url;
            let voice_url = formData.voice_url;

            if (imageFile) {
                const data = await api.uploadFile(imageFile, token);
                image_url = data.url;
            }

            if (voiceFile) {
                const data = await api.uploadFile(voiceFile, token);
                voice_url = data.url;
            }

            await onUpdate({
                ...formData,
                image_url: image_url || undefined,
                voice_url: voice_url || undefined,
            });

            setImageFile(null);
            setVoiceFile(null);
            alert('تغییرات با موفقیت ذخیره شد.');
        } catch (e: any) {
            alert(e?.message || 'خطا در ذخیره تغییرات');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 h-full overflow-hidden">
            {/* Right Column (Media Forms) */}
            <div className="lg:col-span-8 xl:col-span-9 flex flex-col gap-5 pt-4 h-full overflow-y-auto pr-1 order-2 lg:order-1 no-scrollbar">

                <div className="bg-white p-6 rounded-2xl shadow-sm border flex-1 flex flex-col">
                    <h3 className="text-sm font-bold mb-6 text-gray-800 text-right">مدیریت رسانه</h3>

                    {/* Bot Profile Image Section */}
                    <div className="mb-8">
                        <label className="block text-xs font-medium text-gray-500 mb-3 text-right">تصویر پروفایل بات</label>
                        <div
                            className="border-2 border-dashed border-gray-200 rounded-2xl p-8 flex flex-col items-center justify-center bg-gray-50/50 hover:bg-gray-50 transition-colors cursor-pointer"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                className="hidden"
                                accept="image/png, image/jpeg"
                                onChange={handleImageUpload}
                            />

                            <div className="w-24 h-24 rounded-full overflow-hidden mb-3 shadow-md relative group">
                                {previewImage ? (
                                    <img src={previewImage} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    <div className="w-full h-full bg-gray-200 flex items-center justify-center text-gray-400">
                                        <ImageIcon size={32} />
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Upload size={20} className="text-white" />
                                </div>
                            </div>
                            <span className="text-xs font-bold text-gray-600 mb-1">تغییر تصویر</span>
                            <span className="text-[10px] text-gray-400">JPG, PNG (max 2MB)</span>
                        </div>
                    </div>

                    {/* Welcome Voice Message Section */}
                    <div className="mb-8">
                        <label className="block text-xs font-medium text-gray-500 mb-3 text-right">پیام صوتی خوش‌آمدگویی</label>
                        <div className="border border-gray-200 rounded-xl p-4 flex items-center justify-between bg-white">
                            <button
                                onClick={() => voiceInputRef.current?.click()}
                                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors shadow-sm"
                            >
                                انتخاب فایل
                            </button>
                            <input
                                type="file"
                                ref={voiceInputRef}
                                className="hidden"
                                accept="audio/*"
                                onChange={handleVoiceUpload}
                            />

                            <div className="flex items-center gap-3">
                                <div className="text-right">
                                    <p className="text-xs font-bold text-gray-700">
                                        {voiceFile ? voiceFile.name : 'فایل صوتی'}
                                    </p>
                                    <p className="text-[10px] text-gray-400">
                                        {voiceFile ? `${(voiceFile.size / 1024 / 1024).toFixed(2)} MB` : 'هنوز فایلی آپلود نشده است'}
                                    </p>
                                </div>
                                <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-500">
                                    <Mic size={20} />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Save Button */}
                    <div className="flex justify-end mt-auto">
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-colors shadow-lg text-xs font-bold ${isSaving ? 'bg-gray-300 text-gray-600 cursor-not-allowed shadow-gray-200' : 'bg-green-600 text-white hover:bg-green-700 shadow-green-200'}`}
                        >
                            <Save size={16} />
                            {isSaving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Left Column (Bot Preview) */}
            <div className="lg:col-span-4 xl:col-span-3 flex flex-col order-1 lg:order-2 h-full min-h-0">
                <div className="bg-white p-4 rounded-2xl shadow-sm border h-full flex flex-col items-center overflow-hidden relative">

                    {/* Header Section */}
                    <div className="w-full bg-gray-50 rounded-2xl p-4 mb-2 flex flex-col items-center text-center border border-gray-100 shrink-0">
                        <div className="flex items-center gap-2 mb-1">
                            <Bot size={18} className="text-gray-600" />
                            <h3 className="font-bold text-gray-700 text-sm">پیش‌نمایش زنده بات</h3>
                        </div>
                        <p className="text-[10px] text-gray-400">تغییرات شما به صورت آنی در اینجا نمایش داده می‌شود</p>
                    </div>

                    {/* Phone Mockup Container */}
                    <div className="flex-1 w-full flex items-center justify-center overflow-hidden relative">
                        <div className="scale-[0.85] origin-center transform">
                            <BotPreview candidate={{ ...formData, image_url: previewImage || undefined }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MediaTab;
