import React, { useState, useMemo, useRef } from 'react';
import { CandidateData, DashboardStats, Plan, Ticket, TicketMessage } from '../types';
import { Users, UserCheck, Bot, Activity, Search, Edit2, Plus, X, Lock, CreditCard, Eye, EyeOff, Check, MessageSquare, Send, Menu, LayoutDashboard, Key, Paperclip, File, Image, ChevronRight, ChevronLeft } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import QuotesCarousel from './QuotesCarousel';

interface AdminPanelProps {
  candidates: CandidateData[];
  setCandidates: React.Dispatch<React.SetStateAction<CandidateData[]>>;
  plans: Plan[];
  setPlans: React.Dispatch<React.SetStateAction<Plan[]>>;
  tickets: Ticket[];
  setTickets: React.Dispatch<React.SetStateAction<Ticket[]>>;
}

const ITEMS_PER_PAGE = 5;

const AdminPanel: React.FC<AdminPanelProps> = ({ candidates, setCandidates, plans, setPlans, tickets, setTickets }) => {
  const [view, setView] = useState<'DASHBOARD' | 'CANDIDATES' | 'PLANS' | 'TICKETS'>('DASHBOARD');
  const [searchQuery, setSearchQuery] = useState('');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Modals
  const [isCandidateModalOpen, setIsCandidateModalOpen] = useState(false);
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [isResetPasswordModalOpen, setIsResetPasswordModalOpen] = useState(false);
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);

  // Form States
  const [candidateFormData, setCandidateFormData] = useState<Partial<CandidateData>>({});
  const [editingCandidate, setEditingCandidate] = useState<CandidateData | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [resetCandidateId, setResetCandidateId] = useState<string | null>(null);

  const [planFormData, setPlanFormData] = useState<Partial<Plan>>({});
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  
  const [ticketReply, setTicketReply] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- STATS & HELPERS ---
  const stats: DashboardStats = useMemo(() => {
    return {
      totalCandidates: candidates.length,
      activeCandidates: candidates.filter(c => c.isActive).length,
      totalBots: candidates.length,
      activeBots: candidates.filter(c => c.isActive).length,
      totalUsers: candidates.reduce((acc, curr) => acc + curr.userCount, 0),
    };
  }, [candidates]);

  // Filter and Pagination Logic
  const filteredCandidates = useMemo(() => {
      return candidates.filter(c => 
        c.name.includes(searchQuery) || 
        c.username.includes(searchQuery) ||
        c.botName.includes(searchQuery)
      );
  }, [candidates, searchQuery]);

  const totalPages = Math.ceil(filteredCandidates.length / ITEMS_PER_PAGE);
  const paginatedCandidates = filteredCandidates.slice(
      (currentPage - 1) * ITEMS_PER_PAGE,
      currentPage * ITEMS_PER_PAGE
  );

  const openTicketCount = tickets.filter(t => t.status === 'OPEN').length;
  const activeTicket = tickets.find(t => t.id === activeTicketId);

  // --- CANDIDATE ACTIONS ---
  const toggleCandidateStatus = (id: string) => {
    setCandidates(prev => prev.map(c => c.id === id ? { ...c, isActive: !c.isActive } : c));
  };

  const handleEditCandidate = (candidate: CandidateData) => {
    setEditingCandidate(candidate);
    setCandidateFormData(candidate);
    setIsCandidateModalOpen(true);
  };

  const openResetPasswordModal = (id: string) => {
      setResetCandidateId(id);
      setNewPassword('');
      setIsResetPasswordModalOpen(true);
  };

  const submitResetPassword = () => {
      if (resetCandidateId && newPassword) {
          setCandidates(prev => prev.map(c => c.id === resetCandidateId ? { ...c, password: newPassword } : c));
          alert("رمز عبور با موفقیت تغییر کرد.");
          setIsResetPasswordModalOpen(false);
          setResetCandidateId(null);
      }
  };

  const handleAddCandidate = () => {
    setEditingCandidate(null);
    setCandidateFormData({ isActive: true, userCount: 0, province: '', city: '' });
    setIsCandidateModalOpen(true);
  };

  const handleSaveCandidate = () => {
    if (!candidateFormData.name || !candidateFormData.username || !candidateFormData.botName) {
        alert("لطفا فیلدهای اجباری را پر کنید");
        return;
    }
    if (editingCandidate) {
      setCandidates(prev => prev.map(c => c.id === editingCandidate.id ? { ...c, ...candidateFormData } as CandidateData : c));
    } else {
      const newCandidate: CandidateData = {
        id: Math.random().toString(36).substr(2, 9),
        name: candidateFormData.name!,
        username: candidateFormData.username!,
        botName: candidateFormData.botName!,
        botToken: candidateFormData.botToken || 'token_placeholder',
        city: candidateFormData.city || '',
        province: candidateFormData.province || '',
        isActive: true,
        userCount: 0,
        ...candidateFormData
      } as CandidateData;
      setCandidates(prev => [...prev, newCandidate]);
    }
    setIsCandidateModalOpen(false);
  };

  // --- PLAN ACTIONS ---
  const handleEditPlan = (plan: Plan) => {
    setEditingPlan(plan);
    setPlanFormData(plan);
    setIsPlanModalOpen(true);
  };

  const handleAddPlan = () => {
    setEditingPlan(null);
    setPlanFormData({ isVisible: true, features: [], color: '#3b82f6' });
    setIsPlanModalOpen(true);
  };

  const togglePlanVisibility = (id: string) => {
      setPlans(prev => prev.map(p => p.id === id ? { ...p, isVisible: !p.isVisible } : p));
  };

  const handleSavePlan = () => {
      if (!planFormData.title || !planFormData.price) {
          alert("عنوان و قیمت الزامی است");
          return;
      }
      if (editingPlan) {
          setPlans(prev => prev.map(p => p.id === editingPlan.id ? { ...p, ...planFormData } as Plan : p));
      } else {
          const newPlan: Plan = {
              id: Math.random().toString(36).substr(2, 9),
              title: planFormData.title!,
              price: planFormData.price!,
              features: planFormData.features || [],
              isVisible: true,
              color: planFormData.color || '#3b82f6',
              ...planFormData
          } as Plan;
          setPlans(prev => [...prev, newPlan]);
      }
      setIsPlanModalOpen(false);
  };

  // --- TICKET ACTIONS ---
  const handleSendTicketReply = (attachment?: {name: string, type: 'IMAGE'|'FILE'}) => {
      if (!activeTicketId || (!ticketReply.trim() && !attachment)) return;
      
      const newMessage: TicketMessage = {
          id: Math.random().toString(36).substr(2, 9),
          senderId: 'admin',
          senderRole: 'ADMIN',
          text: ticketReply,
          timestamp: Date.now(),
          attachmentName: attachment?.name,
          attachmentType: attachment?.type
      };
      
      setTickets(prev => prev.map(t => {
          if (t.id === activeTicketId) {
              return {
                  ...t,
                  status: 'ANSWERED',
                  messages: [...t.messages, newMessage],
                  lastUpdate: Date.now()
              };
          }
          return t;
      }));
      setTicketReply('');
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      
      const isImage = file.type.startsWith('image/');
      handleSendTicketReply({
          name: file.name,
          type: isImage ? 'IMAGE' : 'FILE'
      });
      // Reset input
      e.target.value = '';
  };

  const MenuItem = ({ id, label, icon, badge }: any) => (
    <button
      onClick={() => { setView(id); setIsMobileMenuOpen(false); }}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
        view === id 
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 font-bold' 
          : 'text-gray-600 hover:bg-gray-100 hover:text-blue-600'
      }`}
    >
      {icon}
      <span className="flex-1 text-right">{label}</span>
      {badge > 0 && (
        <span className="bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full">{badge}</span>
      )}
    </button>
  );

  // --- RENDER ---
  return (
    <div className="flex h-full relative bg-gray-50">
      
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setIsMobileMenuOpen(false)}></div>
      )}

      {/* Sidebar Navigation */}
      <aside className={`
        fixed lg:static inset-y-0 right-0 z-40 w-64 bg-white border-l border-gray-200 transform transition-transform duration-300 ease-in-out flex flex-col
        ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-6 border-b flex items-center gap-2">
           <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
             <LayoutDashboard size={18}/>
           </div>
           <h2 className="font-bold text-gray-800">منوی مدیریت</h2>
        </div>
        
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          <MenuItem id="DASHBOARD" label="داشبورد" icon={<Activity size={20}/>} />
          <MenuItem id="CANDIDATES" label="مدیریت کاندیداها" icon={<Users size={20}/>} />
          <MenuItem id="PLANS" label="اشتراک و پلن‌ها" icon={<CreditCard size={20}/>} />
          <MenuItem id="TICKETS" label="پشتیبانی" icon={<MessageSquare size={20}/>} badge={openTicketCount} />
        </nav>

        <div className="p-4 border-t bg-gray-50">
            <p className="text-xs text-center text-gray-400">نسخه ۱.۲.۰</p>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Mobile Header Trigger */}
        <div className="lg:hidden p-4 bg-white border-b flex justify-between items-center">
            <span className="font-bold text-gray-700">پنل مدیریت</span>
            <button onClick={() => setIsMobileMenuOpen(true)} className="p-2 bg-gray-100 rounded-lg"><Menu/></button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-8">
            {view === 'DASHBOARD' && (
                <div className="space-y-6">
                    {/* Quotes Widget */}
                    <div className="w-full h-48 rounded-2xl overflow-hidden shadow-lg border border-blue-100 relative group">
                        <QuotesCarousel variant="widget" />
                        <div className="absolute top-2 right-2 bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-white text-xs">سخن روز</div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <StatCard icon={<Users />} title="کل کاندیداها" value={stats.totalCandidates} color="bg-blue-500" />
                        <StatCard icon={<UserCheck />} title="کاندیدای فعال" value={stats.activeCandidates} color="bg-green-500" />
                        <StatCard icon={<Bot />} title="کل بات‌ها" value={stats.totalBots} color="bg-purple-500" />
                        <StatCard icon={<Activity />} title="بات‌های فعال" value={stats.activeBots} color="bg-indigo-500" />
                    </div>
                    
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                        <h3 className="text-lg font-bold mb-6 text-gray-700 flex items-center gap-2">
                            <Users size={20} className="text-blue-500"/>
                            آمار جذب مخاطب کاندیداها
                        </h3>
                        <div className="h-80 w-full dir-ltr">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={candidates.slice(0, 10)}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} dy={10} />
                                    <YAxis axisLine={false} tickLine={false} />
                                    <Tooltip 
                                        cursor={{fill: '#f3f4f6'}} 
                                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                    />
                                    <Bar dataKey="userCount" fill="#3b82f6" radius={[6, 6, 0, 0]} barSize={40} name="تعداد کاربر" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>
            )}

      {view === 'CANDIDATES' && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col h-[calc(100vh-150px)]">
          <div className="p-6 border-b flex flex-col md:flex-row justify-between items-center gap-4 bg-gray-50/50">
            <h2 className="font-bold text-lg text-gray-800">لیست کاندیداها</h2>
            <div className="flex gap-3 w-full md:w-auto">
                <div className="relative flex-1 md:w-64">
                    <Search className="absolute right-3 top-3 text-gray-400" size={20} />
                    <input 
                        type="text" 
                        placeholder="جستجو..." 
                        className="w-full pl-4 pr-10 py-2 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <button onClick={handleAddCandidate} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/20">
                    <Plus size={20} />
                    <span className="hidden md:inline">افزودن</span>
                </button>
            </div>
          </div>

          <div className="flex-1 overflow-x-auto overflow-y-auto">
            <table className="w-full text-right">
              <thead className="bg-gray-50 text-gray-500 text-sm font-medium sticky top-0 z-10">
                <tr>
                  <th className="p-4">نام کاندید</th>
                  <th className="p-4">اطلاعات بات</th>
                  <th className="p-4">موقعیت</th>
                  <th className="p-4">وضعیت</th>
                  <th className="p-4 text-center">عملیات</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {paginatedCandidates.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50 transition group">
                    <td className="p-4 align-top">
                        <div className="font-bold text-gray-800">{c.name}</div>
                        <div className="text-xs text-gray-400 mt-1">@{c.username}</div>
                    </td>
                    <td className="p-4 align-top">
                        {/* Fixed Alignment */}
                        <div className="flex flex-col gap-1 items-start dir-ltr">
                            <span className="text-blue-600 font-bold text-sm flex items-center gap-1">
                                {c.botName} <Bot size={14}/>
                            </span>
                            <span className="text-gray-400 text-[10px] font-mono bg-gray-100 px-2 py-0.5 rounded truncate max-w-[150px]" title={c.botToken}>
                                Token: {c.botToken.substring(0, 8)}...
                            </span>
                        </div>
                    </td>
                    <td className="p-4 text-sm text-gray-600 align-top">{c.city}، {c.province}</td>
                    <td className="p-4 align-top">
                      <button onClick={() => toggleCandidateStatus(c.id)} className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${c.isActive ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-red-100 text-red-700 hover:bg-red-200'}`}>
                        {c.isActive ? 'فعال' : 'غیرفعال'}
                      </button>
                    </td>
                    <td className="p-4 align-top">
                        <div className="flex justify-center gap-2 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => handleEditCandidate(c)} className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition" title="ویرایش"><Edit2 size={18} /></button>
                            <button onClick={() => openResetPasswordModal(c.id)} className="p-2 text-gray-500 hover:text-orange-600 hover:bg-orange-50 rounded-lg transition" title="ریست پسورد"><Key size={18} /></button>
                        </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="p-4 border-t flex justify-between items-center bg-gray-50">
             <span className="text-sm text-gray-500">
                نمایش {Math.min((currentPage - 1) * ITEMS_PER_PAGE + 1, filteredCandidates.length)} تا {Math.min(currentPage * ITEMS_PER_PAGE, filteredCandidates.length)} از {filteredCandidates.length}
             </span>
             <div className="flex gap-2">
                 <button 
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    className="p-2 rounded-lg border bg-white hover:bg-gray-100 disabled:opacity-50"
                 >
                     <ChevronRight size={18}/>
                 </button>
                 {Array.from({length: totalPages}, (_, i) => i + 1).map(page => (
                     <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition ${currentPage === page ? 'bg-blue-600 text-white' : 'bg-white border hover:bg-gray-100'}`}
                     >
                         {page}
                     </button>
                 ))}
                 <button 
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    className="p-2 rounded-lg border bg-white hover:bg-gray-100 disabled:opacity-50"
                 >
                     <ChevronLeft size={18}/>
                 </button>
             </div>
          </div>
        </div>
      )}

      {view === 'PLANS' && (
          <div className="space-y-6">
              <div className="flex justify-between items-center">
                  <h2 className="text-xl font-bold text-gray-800">مدیریت پلن‌های اشتراک</h2>
                  <button onClick={handleAddPlan} className="flex items-center gap-2 bg-gray-900 text-white px-4 py-2 rounded-xl hover:bg-gray-800 transition">
                      <Plus size={20} />
                      تعریف پلن
                  </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {plans.map(plan => (
                      <div key={plan.id} className={`bg-white rounded-3xl shadow-sm overflow-hidden border transition hover:shadow-lg ${plan.isVisible ? 'border-gray-100' : 'border-gray-200 opacity-60 grayscale'}`}>
                          <div className="p-6 text-white flex justify-between items-start" style={{backgroundColor: plan.color}}>
                              <div>
                                  <h3 className="font-bold text-lg mb-1">{plan.title}</h3>
                                  <span className="text-white/80 text-xs px-2 py-0.5 bg-white/20 rounded-full">اشتراک ماهانه</span>
                              </div>
                              <div className="flex gap-1">
                                  <button onClick={() => togglePlanVisibility(plan.id)} title={plan.isVisible ? 'غیرفعال کردن (اتمام موجودی)' : 'فعال کردن'} className="p-1.5 hover:bg-white/20 rounded-lg transition">
                                      {plan.isVisible ? <Eye size={18}/> : <EyeOff size={18}/>}
                                  </button>
                                  <button onClick={() => handleEditPlan(plan)} className="p-1.5 hover:bg-white/20 rounded-lg transition"><Edit2 size={18}/></button>
                              </div>
                          </div>
                          <div className="p-6 text-center border-b border-dashed">
                              <div className="text-2xl font-black text-gray-800">{plan.price}</div>
                          </div>
                          <div className="p-6">
                              <ul className="space-y-4">
                                  {plan.features.slice(0, 4).map((feat, idx) => (
                                      <li key={idx} className="flex items-center gap-3 text-gray-600 text-sm">
                                          <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-green-600 shrink-0">
                                            <Check size={12} />
                                          </div>
                                          {feat}
                                      </li>
                                  ))}
                                  {plan.features.length > 4 && (
                                      <li className="text-xs text-gray-400 text-center pt-2">و {plan.features.length - 4} ویژگی دیگر...</li>
                                  )}
                              </ul>
                          </div>
                      </div>
                  ))}
              </div>
          </div>
      )}

      {view === 'TICKETS' && (
          <div className="flex flex-col md:flex-row h-[calc(100vh-140px)] bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              {/* Ticket List */}
              <div className="w-full md:w-80 border-l bg-gray-50 flex flex-col">
                  <div className="p-4 border-b font-bold text-gray-700 bg-white shadow-sm z-10">صندوق پیام‌ها</div>
                  <div className="flex-1 overflow-y-auto">
                    {tickets.map(ticket => (
                        <div 
                            key={ticket.id} 
                            onClick={() => setActiveTicketId(ticket.id)}
                            className={`p-4 border-b cursor-pointer hover:bg-white transition relative ${activeTicketId === ticket.id ? 'bg-white border-r-4 border-r-blue-600' : ''}`}
                        >
                            <div className="flex justify-between items-center mb-1">
                                <span className="font-bold text-sm text-gray-800">{ticket.candidateName}</span>
                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${ticket.status === 'OPEN' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                                    {ticket.status === 'OPEN' ? 'باز' : 'بسته'}
                                </span>
                            </div>
                            <h4 className="text-xs font-medium text-gray-600 mb-1 truncate">{ticket.subject}</h4>
                            <p className="text-[11px] text-gray-400 truncate">{ticket.messages[ticket.messages.length - 1]?.text || 'پیوست فایل'}</p>
                        </div>
                    ))}
                  </div>
              </div>

              {/* Chat View */}
              <div className="flex-1 flex flex-col bg-white">
                  {activeTicket ? (
                      <>
                          <div className="p-4 border-b flex justify-between items-center bg-gray-50/50">
                              <div>
                                  <h3 className="font-bold text-gray-800">{activeTicket.subject}</h3>
                                  <p className="text-xs text-gray-500">گفتگو با {activeTicket.candidateName}</p>
                              </div>
                              <button onClick={() => setActiveTicketId(null)} className="md:hidden p-2 text-gray-500"><X size={20}/></button>
                          </div>
                          
                          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/30">
                              {activeTicket.messages.map(msg => (
                                  <div key={msg.id} className={`flex ${msg.senderRole === 'ADMIN' ? 'justify-end' : 'justify-start'}`}>
                                      <div className={`max-w-[80%] rounded-2xl p-4 text-sm shadow-sm ${msg.senderRole === 'ADMIN' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-white text-gray-800 border rounded-bl-none'}`}>
                                          {msg.text && <p>{msg.text}</p>}
                                          {msg.attachmentName && (
                                              <div className={`mt-2 p-2 rounded flex items-center gap-2 ${msg.senderRole === 'ADMIN' ? 'bg-blue-700/50' : 'bg-gray-100'}`}>
                                                  {msg.attachmentType === 'IMAGE' ? <Image size={16}/> : <File size={16}/>}
                                                  <span className="text-xs truncate max-w-[150px]">{msg.attachmentName}</span>
                                              </div>
                                          )}
                                          <div className={`text-[10px] mt-2 text-left ${msg.senderRole === 'ADMIN' ? 'text-blue-200' : 'text-gray-400'}`}>
                                              {new Date(msg.timestamp).toLocaleTimeString('fa-IR', {hour: '2-digit', minute:'2-digit'})}
                                          </div>
                                      </div>
                                  </div>
                              ))}
                          </div>

                          <div className="p-4 border-t bg-white flex gap-2">
                              <input 
                                  type="file" 
                                  className="hidden" 
                                  ref={fileInputRef}
                                  onChange={handleFileUpload}
                              />
                              <button 
                                onClick={() => fileInputRef.current?.click()}
                                className="p-3 text-gray-500 hover:bg-gray-100 rounded-xl transition"
                                title="ارسال فایل"
                              >
                                  <Paperclip size={20} />
                              </button>
                              <input 
                                  type="text" 
                                  className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition"
                                  placeholder="پیام خود را بنویسید..."
                                  value={ticketReply}
                                  onChange={(e) => setTicketReply(e.target.value)}
                                  onKeyPress={(e) => e.key === 'Enter' && handleSendTicketReply()}
                              />
                              <button 
                                  onClick={() => handleSendTicketReply()}
                                  className="bg-blue-600 text-white p-3 rounded-xl hover:bg-blue-700 transition shadow-lg shadow-blue-500/30"
                              >
                                  <Send size={20} className={!ticketReply ? 'opacity-50' : ''}/>
                              </button>
                          </div>
                      </>
                  ) : (
                      <div className="flex-1 flex flex-col items-center justify-center text-gray-300">
                          <MessageSquare size={64} className="mb-4 opacity-20"/>
                          <p>یک گفتگو را انتخاب کنید</p>
                      </div>
                  )}
              </div>
          </div>
      )}
      
        </div>
      </div>

      {/* Candidate Modal */}
      {isCandidateModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl animate-fade-in-up">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">{editingCandidate ? 'ویرایش کاندید' : 'افزودن کاندید جدید'}</h2>
              <button onClick={() => setIsCandidateModalOpen(false)} className="text-gray-400 hover:text-red-500"><X /></button>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
               <Input label="نام و نام خانوادگی" value={candidateFormData.name || ''} onChange={e => setCandidateFormData({...candidateFormData, name: e.target.value})} />
               <Input label="نام کاربری (ورود)" value={candidateFormData.username || ''} onChange={e => setCandidateFormData({...candidateFormData, username: e.target.value})} />
               <Input label="نام نمایشی بات (@bot)" value={candidateFormData.botName || ''} onChange={e => setCandidateFormData({...candidateFormData, botName: e.target.value})} />
               <Input label="توکن بات" value={candidateFormData.botToken || ''} onChange={e => setCandidateFormData({...candidateFormData, botToken: e.target.value})} />
               <Input label="استان" value={candidateFormData.province || ''} onChange={e => setCandidateFormData({...candidateFormData, province: e.target.value})} />
               <Input label="شهر" value={candidateFormData.city || ''} onChange={e => setCandidateFormData({...candidateFormData, city: e.target.value})} />
            </div>
            <div className="p-6 border-t bg-gray-50 flex justify-end gap-3">
              <button onClick={() => setIsCandidateModalOpen(false)} className="px-6 py-2.5 text-gray-600 hover:bg-gray-200 rounded-xl transition">انصراف</button>
              <button onClick={handleSaveCandidate} className="px-8 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-500/30 transition">ذخیره اطلاعات</button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {isResetPasswordModalOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
            <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl animate-fade-in-up">
                <div className="flex justify-between items-center p-6 border-b">
                <h2 className="text-xl font-bold text-gray-800">تغییر رمز عبور</h2>
                <button onClick={() => setIsResetPasswordModalOpen(false)} className="text-gray-400 hover:text-red-500"><X /></button>
                </div>
                <div className="p-6 space-y-4">
                    <Input 
                        label="رمز عبور جدید" 
                        type="text" // Shown as text so admin can see it, change to password if needed
                        value={newPassword} 
                        onChange={e => setNewPassword(e.target.value)} 
                    />
                    <p className="text-xs text-gray-500">رمز عبور جدید را برای کاندید وارد کنید. پس از ذخیره، کاندید باید با این رمز وارد شود.</p>
                </div>
                <div className="p-6 border-t bg-gray-50 flex justify-end gap-3">
                <button onClick={() => setIsResetPasswordModalOpen(false)} className="px-6 py-2.5 text-gray-600 hover:bg-gray-200 rounded-xl transition">انصراف</button>
                <button onClick={submitResetPassword} className="px-8 py-2.5 bg-orange-500 text-white rounded-xl hover:bg-orange-600 shadow-lg shadow-orange-500/30 transition">تغییر رمز</button>
                </div>
            </div>
          </div>
      )}

      {/* Plan Modal */}
      {isPlanModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl animate-fade-in-up">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-800">{editingPlan ? 'ویرایش پلن' : 'ایجاد پلن جدید'}</h2>
              <button onClick={() => setIsPlanModalOpen(false)} className="text-gray-400 hover:text-red-500"><X /></button>
            </div>
            <div className="p-6 space-y-4">
               <Input label="عنوان پلن" value={planFormData.title || ''} onChange={e => setPlanFormData({...planFormData, title: e.target.value})} />
               <Input label="قیمت (مثلا: ۵۰۰,۰۰۰ تومان)" value={planFormData.price || ''} onChange={e => setPlanFormData({...planFormData, price: e.target.value})} />
               
               <div>
                   <label className="block text-sm font-medium text-gray-700 mb-1">ویژگی‌ها (با ویرگول جدا کنید)</label>
                   <textarea 
                        className="w-full border rounded-xl p-3 focus:ring-2 focus:ring-blue-500 outline-none transition"
                        rows={3}
                        value={planFormData.features ? planFormData.features.join(',') : ''}
                        onChange={e => setPlanFormData({...planFormData, features: e.target.value.split(',')})}
                        placeholder="بات اختصاصی, پشتیبانی تلفنی, دامنه رایگان"
                   />
               </div>
               
               <div>
                   <label className="block text-sm font-medium text-gray-700 mb-1">رنگ کارت</label>
                   <div className="flex gap-2 items-center">
                       <input 
                         type="color"
                         className="w-12 h-12 rounded-lg border cursor-pointer"
                         value={planFormData.color || '#3b82f6'}
                         onChange={e => setPlanFormData({...planFormData, color: e.target.value})}
                       />
                       <input 
                         type="text"
                         className="flex-1 border rounded-xl px-4 py-2.5 text-sm dir-ltr"
                         placeholder="#3b82f6"
                         value={planFormData.color || ''}
                         onChange={e => setPlanFormData({...planFormData, color: e.target.value})}
                       />
                   </div>
               </div>
            </div>
            <div className="p-6 border-t bg-gray-50 flex justify-end gap-3">
              <button onClick={() => setIsPlanModalOpen(false)} className="px-6 py-2.5 text-gray-600 hover:bg-gray-200 rounded-xl transition">انصراف</button>
              <button onClick={handleSavePlan} className="px-8 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-500/30 transition">ذخیره پلن</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatCard = ({ icon, title, value, color }: { icon: React.ReactNode, title: string, value: number, color: string }) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm flex items-center justify-between border border-gray-100 hover:shadow-md transition cursor-default">
    <div>
      <p className="text-gray-500 text-sm mb-1">{title}</p>
      <h3 className="text-2xl font-black text-gray-800">{value}</h3>
    </div>
    <div className={`p-4 rounded-xl text-white ${color} shadow-lg shadow-${color.replace('bg-', '')}/30`}>
      {icon}
    </div>
  </div>
);

const Input = ({ label, value, onChange, type = 'text' }: { label: string, value: string, onChange: (e: React.ChangeEvent<HTMLInputElement>) => void, type?: string }) => (
  <div className="flex flex-col gap-1">
    <label className="text-sm font-medium text-gray-700">{label}</label>
    <input 
      type={type} 
      value={value} 
      onChange={onChange}
      className="border rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition bg-gray-50 focus:bg-white"
    />
  </div>
);

export default AdminPanel;