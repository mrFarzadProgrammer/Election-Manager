import React, { useState, useRef } from 'react';
import { CandidateData, Plan, Ticket, TicketMessage } from '../types';
import { Users, Bot, Save, ExternalLink, Image as ImageIcon, Mic, FileText, MapPin, Lightbulb, CreditCard, MessageCircle, Send, Plus, Check, Menu, LayoutDashboard, Settings, Clock, Shield, Instagram, Link, AlertTriangle, Paperclip, Image, File, Lock, Upload, X, Music } from 'lucide-react';
import BotPreview from './BotPreview';
import QuotesCarousel from './QuotesCarousel';

interface CandidatePanelProps {
  candidate: CandidateData;
  onUpdate: (updatedData: Partial<CandidateData>) => void;
  plans: Plan[];
  tickets: Ticket[];
  setTickets: React.Dispatch<React.SetStateAction<Ticket[]>>;
}

const CandidatePanel: React.FC<CandidatePanelProps> = ({ candidate, onUpdate, plans, tickets, setTickets }) => {
  const [activeTab, setActiveTab] = useState<'PROFILE' | 'MEDIA' | 'CONTENT' | 'BOT_SETTINGS' | 'PLANS' | 'SUPPORT'>('PROFILE');
  const [formData, setFormData] = useState<CandidateData>(candidate);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Ticket State
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const [newTicketSubject, setNewTicketSubject] = useState('');
  const [newTicketMsg, setNewTicketMsg] = useState('');
  const [replyMsg, setReplyMsg] = useState('');
  const [isNewTicketMode, setIsNewTicketMode] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const myTickets = tickets.filter(t => t.candidateId === candidate.id).sort((a,b) => b.lastUpdate - a.lastUpdate);
  const activeTicket = myTickets.find(t => t.id === activeTicketId);

  const handleSave = () => {
    onUpdate(formData);
    alert('تغییرات با موفقیت ذخیره شد.');
  };

  const handleChange = (field: keyof CandidateData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Helper for File Uploads (Simulated)
  const handleFileChange = (field: keyof CandidateData, e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
          const objectUrl = URL.createObjectURL(file);
          setFormData(prev => ({ ...prev, [field]: objectUrl }));
      }
  };
  
  const handleSocialChange = (field: 'telegramChannel' | 'telegramGroup' | 'instagram', value: string) => {
    setFormData(prev => ({
        ...prev,
        socials: { ...prev.socials, [field]: value }
    }));
  };

  const handleBotConfigChange = (field: string, value: any) => {
      setFormData(prev => ({
          ...prev,
          botConfig: { ...prev.botConfig, [field]: value, badWords: prev.botConfig?.badWords || [], blockLinks: prev.botConfig?.blockLinks || false, groupLockEnabled: prev.botConfig?.groupLockEnabled || false }
      }));
  };

  // Support Handlers
  const handleCreateTicket = () => {
      if (!newTicketSubject.trim() || !newTicketMsg.trim()) return;
      const newTicket: Ticket = {
          id: Math.random().toString(36).substr(2, 9),
          candidateId: candidate.id,
          candidateName: candidate.name,
          subject: newTicketSubject,
          status: 'OPEN',
          lastUpdate: Date.now(),
          messages: [
              {
                  id: Math.random().toString(36).substr(2, 9),
                  senderId: candidate.id,
                  senderRole: 'CANDIDATE',
                  text: newTicketMsg,
                  timestamp: Date.now()
              }
          ]
      };
      setTickets(prev => [...prev, newTicket]);
      setNewTicketSubject('');
      setNewTicketMsg('');
      setIsNewTicketMode(false);
      setActiveTicketId(newTicket.id);
  };

  const handleReplyTicket = (attachment?: {name: string, type: 'IMAGE'|'FILE', url?: string}) => {
      if (!activeTicketId || (!replyMsg.trim() && !attachment)) return;
      
      const newMessage: TicketMessage = {
          id: Math.random().toString(36).substr(2, 9),
          senderId: candidate.id,
          senderRole: 'CANDIDATE',
          text: replyMsg, // Use the URL if attachment
          timestamp: Date.now(),
          attachmentName: attachment?.name,
          attachmentType: attachment?.type
      };
      
      setTickets(prev => prev.map(t => {
          if (t.id === activeTicketId) {
              return {
                  ...t,
                  status: 'OPEN', // Re-open if replying
                  lastUpdate: Date.now(),
                  messages: [...t.messages, newMessage]
              };
          }
          return t;
      }));
      setReplyMsg('');
  };

  const handleTicketFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      
      const isImage = file.type.startsWith('image/');
      const url = URL.createObjectURL(file); // Create fake URL for preview
      
      handleReplyTicket({
          name: file.name,
          type: isImage ? 'IMAGE' : 'FILE',
          url: url
      });
      // Reset input
      e.target.value = '';
  };

  const MenuItem = ({ id, label, icon }: any) => (
    <button
      onClick={() => { setActiveTab(id); setIsMobileMenuOpen(false); }}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
        activeTab === id 
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 font-bold' 
          : 'text-gray-600 hover:bg-gray-100 hover:text-blue-600'
      }`}
    >
      {icon}
      <span className="flex-1 text-right">{label}</span>
    </button>
  );

  return (
    <div className="flex h-full relative bg-gray-50">
        {/* Mobile Menu Overlay */}
        {isMobileMenuOpen && (
            <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setIsMobileMenuOpen(false)}></div>
        )}

        {/* Sidebar Navigation */}
        <aside className={`
            fixed lg:static inset-y-0 right-0 z-40 w-64 bg-white border-l border-gray-200 transform transition-transform duration-300 ease-in-out flex flex-col shrink-0
            ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}
        `}>
            <div className="p-6 border-b flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
                    <LayoutDashboard size={18}/>
                </div>
                <h2 className="font-bold text-gray-800">داشبورد کاندیدا</h2>
            </div>
            
            <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                <MenuItem id="PROFILE" label="اطلاعات و آمار" icon={<FileText size={20}/>} />
                <MenuItem id="MEDIA" label="رسانه و فایل" icon={<ImageIcon size={20}/>} />
                <MenuItem id="CONTENT" label="برنامه‌های من" icon={<Lightbulb size={20}/>} />
                <MenuItem id="BOT_SETTINGS" label="تنظیمات بات" icon={<Settings size={20}/>} />
                <MenuItem id="PLANS" label="لیست پلن‌ها" icon={<CreditCard size={20}/>} />
                <MenuItem id="SUPPORT" label="پشتیبانی" icon={<MessageCircle size={20}/>} />
            </nav>

            <div className="p-4 border-t bg-gray-50">
                 <div className="text-xs text-center text-gray-500 bg-blue-50 p-3 rounded-lg border border-blue-100">
                    <p className="font-bold text-blue-800 mb-1">پلن فعال: پایه</p>
                    <p>اعتبار: ۲۹ روز</p>
                 </div>
            </div>
        </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        
        {/* Mobile Header Trigger */}
        <div className="lg:hidden p-4 bg-white border-b flex justify-between items-center">
            <span className="font-bold text-gray-700">پنل کاربری</span>
            <button onClick={() => setIsMobileMenuOpen(true)} className="p-2 bg-gray-100 rounded-lg"><Menu/></button>
        </div>

        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
             
             {/* Dynamic Content */}
             <div className="flex-1 overflow-y-auto p-4 md:p-8">
                {activeTab === 'PROFILE' && (
                    <div className="space-y-6">
                        {/* Quotes Widget - Only on Profile/Dashboard page */}
                        <div className="w-full h-40 rounded-2xl overflow-hidden shadow-sm border border-blue-100 relative group mb-6">
                             <QuotesCarousel variant="widget" />
                             <div className="absolute top-2 right-2 bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-white text-xs">سخن روز</div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-gradient-to-l from-blue-600 to-blue-500 text-white p-6 rounded-2xl shadow-lg shadow-blue-500/20 flex items-center justify-between">
                                <div>
                                    <p className="text-blue-100 mb-1">تعداد هواداران</p>
                                    <h2 className="text-4xl font-bold">{candidate.userCount}</h2>
                                </div>
                                <div className="bg-white/20 p-3 rounded-xl"><Users size={32}/></div>
                            </div>
                            
                            <a href={`https://t.me/${candidate.botName.replace('@','')}`} target="_blank" rel="noreferrer" 
                            className="bg-white border border-gray-200 p-6 rounded-2xl shadow-sm flex items-center justify-between hover:border-blue-400 hover:shadow-md transition group">
                                <div>
                                    <p className="text-gray-500 mb-1">لینک بات شما</p>
                                    <h2 className="text-xl font-bold text-gray-800 group-hover:text-blue-600 dir-ltr text-right">{candidate.botName}</h2>
                                </div>
                                <div className="bg-gray-100 p-3 rounded-xl group-hover:bg-blue-50 text-gray-600 group-hover:text-blue-600"><ExternalLink size={32}/></div>
                            </a>
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h3 className="font-bold text-gray-800 border-b pb-4 mb-4">اطلاعات پایه</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <Input label="نام کامل" value={formData.name} onChange={(e) => handleChange('name', e.target.value)} disabled />
                                <Input label="شهر" value={formData.city} onChange={(e) => handleChange('city', e.target.value)} />
                                <Input label="استان" value={formData.province} onChange={(e) => handleChange('province', e.target.value)} />
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-gray-700 mb-2">آدرس ستاد انتخاباتی</label>
                                    <div className="relative">
                                        <MapPin className="absolute right-3 top-3 text-gray-400" size={18}/>
                                        <textarea 
                                            rows={3}
                                            className="w-full border rounded-xl pr-10 pl-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50 focus:bg-white"
                                            value={formData.address || ''}
                                            onChange={(e) => handleChange('address', e.target.value)}
                                            placeholder="آدرس دقیق ستاد مرکزی..."
                                        />
                                    </div>
                                </div>
                            </div>
                            
                            <h3 className="font-bold text-gray-800 border-b pb-4 mb-4 mt-8 flex items-center gap-2"><Link size={20}/> شبکه‌های اجتماعی</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <Input 
                                    label="کانال تلگرام" 
                                    value={formData.socials?.telegramChannel || ''} 
                                    onChange={(e) => handleSocialChange('telegramChannel', e.target.value)} 
                                    placeholder="https://t.me/your_channel" 
                                    icon={<Send size={18} className="text-blue-400"/>} 
                                />
                                <Input 
                                    label="گروه تلگرام" 
                                    value={formData.socials?.telegramGroup || ''} 
                                    onChange={(e) => handleSocialChange('telegramGroup', e.target.value)} 
                                    placeholder="https://t.me/your_group" 
                                    icon={<Users size={18} className="text-blue-400"/>} 
                                />
                                <Input 
                                    label="اینستاگرام" 
                                    value={formData.socials?.instagram || ''} 
                                    onChange={(e) => handleSocialChange('instagram', e.target.value)} 
                                    placeholder="https://instagram.com/your_page" 
                                    icon={<Instagram size={18} className="text-pink-500"/>} 
                                />
                            </div>

                            <SaveButton onSave={handleSave} />
                        </div>
                    </div>
                )}

                {activeTab === 'MEDIA' && (
                    <div className="space-y-6 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                         <h3 className="font-bold text-lg text-gray-800 border-b pb-4">مدیریت رسانه</h3>
                         
                         {/* Photo Upload */}
                         <div className="space-y-2">
                             <label className="font-medium text-gray-700 block">تصویر پروفایل بات</label>
                             <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center bg-gray-50 hover:bg-blue-50 hover:border-blue-300 transition cursor-pointer relative group">
                                 <input 
                                    type="file" 
                                    accept="image/*"
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                    onChange={(e) => handleFileChange('photoUrl', e)}
                                 />
                                 <div className="flex flex-col items-center gap-2 text-gray-400 group-hover:text-blue-500">
                                     {formData.photoUrl ? (
                                         <img src={formData.photoUrl} alt="Preview" className="w-32 h-32 rounded-full object-cover shadow-md mb-2"/>
                                     ) : (
                                         <Upload size={48} className="mb-2"/>
                                     )}
                                     <span className="text-sm font-bold">{formData.photoUrl ? 'تغییر تصویر' : 'آپلود تصویر جدید'}</span>
                                     <span className="text-xs">JPG, PNG (max 2MB)</span>
                                 </div>
                             </div>
                         </div>

                         {/* Voice Upload */}
                         <div className="space-y-2 pt-4 border-t">
                             <label className="font-medium text-gray-700 block">پیام صوتی خوش‌آمدگویی</label>
                             <div className="flex items-center gap-4 border rounded-xl p-4 bg-gray-50">
                                 <div className="bg-blue-100 text-blue-600 p-3 rounded-full">
                                     <Mic size={24}/>
                                 </div>
                                 <div className="flex-1">
                                     <p className="text-sm font-bold text-gray-700">فایل صوتی</p>
                                     {formData.voiceUrl ? (
                                         <audio controls src={formData.voiceUrl} className="h-8 mt-1 w-full max-w-xs"/>
                                     ) : (
                                         <p className="text-xs text-gray-500">هنوز فایلی آپلود نشده است</p>
                                     )}
                                 </div>
                                 <div className="relative overflow-hidden">
                                     <button className="bg-white border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition">انتخاب فایل</button>
                                     <input 
                                        type="file" 
                                        accept="audio/*"
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                        onChange={(e) => handleFileChange('voiceUrl', e)}
                                     />
                                 </div>
                             </div>
                         </div>

                         <SaveButton onSave={handleSave} />
                    </div>
                )}

                {activeTab === 'CONTENT' && (
                    <div className="space-y-6 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                         <h3 className="font-bold text-lg text-gray-800 border-b pb-4">محتوای تبلیغاتی</h3>
                        <div className="space-y-2">
                             <label className="font-bold text-gray-700">شعار انتخاباتی</label>
                             <input 
                                className="w-full text-xl font-bold text-center text-blue-800 border-2 border-blue-100 rounded-xl py-4 focus:ring-2 focus:ring-blue-500 outline-none bg-blue-50/50"
                                value={formData.slogan || ''}
                                onChange={(e) => handleChange('slogan', e.target.value)}
                                placeholder="شعار کوتاه و جذاب..."
                             />
                        </div>
                        <div className="space-y-2">
                             <label className="font-medium text-gray-700">رزومه و سوابق</label>
                             <textarea 
                                rows={6}
                                className="w-full border rounded-xl p-3 focus:ring-2 focus:ring-blue-500 outline-none bg-gray-50 focus:bg-white transition"
                                value={formData.resume || ''}
                                onChange={(e) => handleChange('resume', e.target.value)}
                                placeholder="سوابق تحصیلی و اجرایی خود را بنویسید..."
                             />
                        </div>
                        <div className="space-y-2">
                             <label className="font-medium text-gray-700">ایده‌ها و برنامه‌ها</label>
                             <textarea 
                                rows={6}
                                className="w-full border rounded-xl p-3 focus:ring-2 focus:ring-blue-500 outline-none bg-gray-50 focus:bg-white transition"
                                value={formData.ideas || ''}
                                onChange={(e) => handleChange('ideas', e.target.value)}
                                placeholder="برنامه های آتی شما..."
                             />
                        </div>
                        <SaveButton onSave={handleSave} />
                    </div>
                )}
                
                {activeTab === 'BOT_SETTINGS' && (
                    <div className="space-y-6">
                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                             <h3 className="font-bold text-lg text-gray-800 border-b pb-4 mb-4 flex items-center gap-2"><Clock className="text-blue-600"/> مدیریت زمان گروه</h3>
                             <div className="flex items-center gap-4 mb-6">
                                 <label className="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" className="sr-only peer" checked={formData.botConfig?.groupLockEnabled || false} onChange={e => handleBotConfigChange('groupLockEnabled', e.target.checked)} />
                                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:right-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                    <span className="mr-3 text-sm font-medium text-gray-700">فعال‌سازی قفل خودکار</span>
                                  </label>
                             </div>
                             <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 transition-opacity ${formData.botConfig?.groupLockEnabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
                                 <Input label="ساعت شروع قفل" type="time" value={formData.botConfig?.lockStartTime || ''} onChange={(e) => handleBotConfigChange('lockStartTime', e.target.value)} />
                                 <Input label="ساعت پایان قفل" type="time" value={formData.botConfig?.lockEndTime || ''} onChange={(e) => handleBotConfigChange('lockEndTime', e.target.value)} />
                             </div>
                             <p className="text-xs text-gray-500 mt-2 bg-blue-50 p-2 rounded inline-block">در ساعات مشخص شده، گروه به صورت خودکار بسته می‌شود و کسی نمیتواند پیام ارسال کند.</p>
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                             <h3 className="font-bold text-lg text-gray-800 border-b pb-4 mb-4 flex items-center gap-2"><Shield className="text-red-600"/> فیلترینگ و محتوا</h3>
                             
                             <div className="flex items-center gap-4 mb-6">
                                 <label className="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" className="sr-only peer" checked={formData.botConfig?.blockLinks || false} onChange={e => handleBotConfigChange('blockLinks', e.target.checked)} />
                                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:right-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                                    <span className="mr-3 text-sm font-medium text-gray-700">جلوگیری از ارسال لینک (ضد تبلیغ)</span>
                                  </label>
                             </div>

                             <div className="space-y-2">
                                 <label className="font-medium text-gray-700 flex items-center gap-1">
                                    <AlertTriangle size={16} className="text-orange-500"/>
                                    کلمات ممنوعه (فیلتر فحاشی)
                                 </label>
                                 <textarea 
                                    rows={4}
                                    className="w-full border rounded-xl p-3 focus:ring-2 focus:ring-red-500 outline-none bg-gray-50 focus:bg-white transition"
                                    value={formData.botConfig?.badWords ? formData.botConfig.badWords.join(',') : ''}
                                    onChange={(e) => handleBotConfigChange('badWords', e.target.value.split(','))}
                                    placeholder="کلمات را با ویرگول جدا کنید (مثلا: توهین, دروغ, ...)"
                                 />
                                 <p className="text-xs text-gray-500">اگر کاربری از این کلمات استفاده کند، پیام او به صورت خودکار حذف می‌شود.</p>
                             </div>
                        </div>
                        <SaveButton onSave={handleSave} />
                    </div>
                )}

                {activeTab === 'PLANS' && (
                    <div className="space-y-6">
                        <div className="bg-blue-600 text-white p-6 rounded-2xl shadow-lg mb-8">
                            <h2 className="text-2xl font-bold mb-2">طرح‌های عضویت و اشتراک</h2>
                            <p className="opacity-90">با ارتقای پنل خود، به امکانات ویژه‌ای مثل بات اختصاصی و مدیریت هوشمند گروه دسترسی پیدا کنید.</p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {plans.filter(p => p.isVisible).map(plan => (
                                <div key={plan.id} className="bg-white rounded-3xl shadow-sm overflow-hidden border border-gray-200 hover:shadow-xl hover:-translate-y-1 transition duration-300 flex flex-col">
                                    <div className="p-6 text-white text-center" style={{backgroundColor: plan.color}}>
                                        <h3 className="font-bold text-xl">{plan.title}</h3>
                                        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full mt-2 inline-block">پیشنهاد ادمین</span>
                                    </div>
                                    <div className="p-6 text-center border-b border-dashed bg-gray-50">
                                        <div className="text-3xl font-black text-gray-800">{plan.price}</div>
                                        <p className="text-gray-400 text-xs mt-1">ماهانه</p>
                                    </div>
                                    <div className="p-6 flex-1">
                                        <ul className="space-y-4 mb-8">
                                            {plan.features.map((feat, idx) => (
                                                <li key={idx} className="flex items-center gap-2 text-gray-600 text-sm">
                                                    <div className="bg-green-100 text-green-600 rounded-full p-0.5"><Check size={14} /></div>
                                                    {feat}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="p-6 pt-0 mt-auto">
                                        <button className="w-full py-3 border-2 border-blue-600 text-blue-600 rounded-xl font-bold hover:bg-blue-600 hover:text-white transition">
                                            خرید اشتراک
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === 'SUPPORT' && (
                    <div className="flex flex-col md:flex-row h-[calc(100vh-140px)] gap-4">
                        {/* List / Create Button */}
                        <div className="w-full md:w-1/3 border border-gray-200 bg-white rounded-2xl overflow-hidden flex flex-col shadow-sm">
                             <div className="p-4 bg-gray-50 border-b flex justify-between items-center">
                                 <span className="font-bold text-sm text-gray-700">تیکت‌های من</span>
                                 <button onClick={() => { setIsNewTicketMode(true); setActiveTicketId(null); }} className="text-blue-600 bg-blue-50 hover:bg-blue-100 p-2 rounded-lg transition">
                                     <Plus size={18}/>
                                 </button>
                             </div>
                             <div className="flex-1 overflow-y-auto">
                                 {myTickets.map(ticket => (
                                     <div 
                                        key={ticket.id} 
                                        onClick={() => { setActiveTicketId(ticket.id); setIsNewTicketMode(false); }}
                                        className={`p-4 border-b cursor-pointer hover:bg-gray-50 transition relative ${activeTicketId === ticket.id ? 'bg-blue-50 border-r-4 border-r-blue-600' : ''}`}
                                     >
                                         <div className="flex justify-between mb-1">
                                             <span className="font-bold text-sm text-gray-800">{ticket.subject}</span>
                                             <span className={`text-[10px] px-2 py-0.5 rounded-full flex items-center ${ticket.status === 'ANSWERED' ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
                                                 {ticket.status === 'ANSWERED' ? 'پاسخ داده' : 'در انتظار'}
                                             </span>
                                         </div>
                                         <p className="text-xs text-gray-400 truncate">{ticket.messages[ticket.messages.length - 1]?.text || 'پیوست فایل'}</p>
                                     </div>
                                 ))}
                             </div>
                        </div>

                        {/* Chat Area / New Ticket Form */}
                        <div className="flex-1 border border-gray-200 rounded-2xl overflow-hidden flex flex-col bg-white shadow-sm">
                            {isNewTicketMode ? (
                                <div className="p-6 flex flex-col gap-4 animate-fade-in">
                                    <h3 className="font-bold text-lg text-gray-700">ارسال تیکت جدید</h3>
                                    <input 
                                        className="border p-4 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50 focus:bg-white transition"
                                        placeholder="موضوع تیکت (مثلا: مشکل در پرداخت)"
                                        value={newTicketSubject}
                                        onChange={e => setNewTicketSubject(e.target.value)}
                                    />
                                    <textarea 
                                        className="border p-4 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 h-48 bg-gray-50 focus:bg-white transition"
                                        placeholder="توضیحات مشکل یا درخواست خود را بنویسید..."
                                        value={newTicketMsg}
                                        onChange={e => setNewTicketMsg(e.target.value)}
                                    />
                                    <button 
                                        onClick={handleCreateTicket}
                                        className="bg-blue-600 text-white py-3 rounded-xl font-bold hover:bg-blue-700 transition shadow-lg shadow-blue-500/30"
                                    >
                                        ارسال تیکت
                                    </button>
                                </div>
                            ) : activeTicket ? (
                                <>
                                    <div className="p-4 bg-white border-b shadow-sm flex items-center justify-between">
                                        <div>
                                            <h3 className="font-bold text-gray-800">{activeTicket.subject}</h3>
                                            <span className="text-xs text-gray-500">شناسه تیکت: #{activeTicket.id}</span>
                                        </div>
                                    </div>
                                    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/50">
                                        {activeTicket.messages.map(msg => (
                                            <div key={msg.id} className={`flex ${msg.senderRole === 'CANDIDATE' ? 'justify-end' : 'justify-start'}`}>
                                                 <div className={`max-w-[80%] rounded-2xl p-4 text-sm shadow-sm ${msg.senderRole === 'CANDIDATE' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-white text-gray-800 border rounded-bl-none'}`}>
                                                     {msg.text && <p>{msg.text}</p>}
                                                     {msg.attachmentName && (
                                                        <div className={`mt-2 p-2 rounded flex items-center gap-2 ${msg.senderRole === 'CANDIDATE' ? 'bg-blue-700/50' : 'bg-gray-100'}`}>
                                                            {msg.attachmentType === 'IMAGE' ? <Image size={16}/> : <File size={16}/>}
                                                            <span className="text-xs truncate max-w-[150px]">{msg.attachmentName}</span>
                                                        </div>
                                                     )}
                                                     <div className={`text-[10px] mt-2 text-left ${msg.senderRole === 'CANDIDATE' ? 'text-blue-200' : 'text-gray-400'}`}>
                                                         {new Date(msg.timestamp).toLocaleTimeString('fa-IR', {hour: '2-digit', minute:'2-digit'})}
                                                     </div>
                                                 </div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="p-4 bg-white border-t flex gap-2">
                                        <input 
                                            type="file" 
                                            className="hidden" 
                                            ref={fileInputRef}
                                            onChange={handleTicketFileUpload}
                                        />
                                        <button 
                                            onClick={() => fileInputRef.current?.click()}
                                            className="p-3 text-gray-500 hover:bg-gray-100 rounded-xl transition"
                                            title="ارسال فایل"
                                        >
                                            <Paperclip size={20} />
                                        </button>
                                        <input 
                                            className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition"
                                            placeholder="پاسخ..."
                                            value={replyMsg}
                                            onChange={e => setReplyMsg(e.target.value)}
                                            onKeyPress={e => e.key === 'Enter' && handleReplyTicket()}
                                        />
                                        <button onClick={() => handleReplyTicket()} className="bg-blue-600 text-white p-3 rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/20">
                                            <Send size={20} className={!replyMsg ? 'opacity-50' : ''}/>
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="flex-1 flex flex-col items-center justify-center text-gray-300">
                                    <MessageCircle size={64} className="mb-4 opacity-20"/>
                                    <p>جهت مشاهده گفتگو یا ارسال پیام جدید، یک تیکت را انتخاب کنید</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
             </div>

             {/* Live Preview Sidebar (Right LTR / Left RTL) - Keep fixed if space allows, or stack */}
             {activeTab !== 'SUPPORT' && activeTab !== 'PLANS' && activeTab !== 'BOT_SETTINGS' && (
                 <div className="hidden xl:flex w-[400px] border-r bg-gray-50 flex-col p-6 items-center justify-start border-t lg:border-t-0 shrink-0 h-full overflow-y-auto">
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 w-full mb-4">
                         <h3 className="font-bold text-gray-600 mb-2 flex items-center gap-2"><Bot size={18}/> پیش‌نمایش زنده بات</h3>
                         <p className="text-xs text-gray-400">تغییرات شما به صورت آنی در اینجا نمایش داده می‌شود.</p>
                    </div>
                    <BotPreview candidate={formData} />
                 </div>
             )}
        </div>
      </div>
    </div>
  );
};

const SaveButton = ({ onSave }: { onSave: () => void }) => (
    <div className="mt-8 flex justify-end">
        <button 
            onClick={onSave}
            className="flex items-center gap-2 bg-green-600 text-white px-8 py-3 rounded-xl hover:bg-green-700 shadow-lg shadow-green-500/30 transition transform hover:-translate-y-1"
        >
            <Save size={20} />
            ذخیره تغییرات
        </button>
    </div>
);

const Input = ({ label, value, onChange, placeholder, icon, disabled, type = 'text' }: any) => (
    <div className="flex flex-col gap-2 w-full">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <div className="relative">
            {icon && <div className="absolute right-3 top-3 text-gray-400">{icon}</div>}
            <input 
                type={type}
                value={value} 
                onChange={onChange}
                disabled={disabled}
                placeholder={placeholder}
                className={`w-full border rounded-xl py-2.5 ${icon ? 'pr-10' : 'px-4'} ${disabled ? 'bg-gray-100 text-gray-500' : 'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-gray-50 focus:bg-white'} outline-none transition`}
            />
        </div>
    </div>
);

export default CandidatePanel;