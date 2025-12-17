import React, { useState } from 'react';
import { User, CandidateData, Role, Plan, Ticket } from './types';
import AdminPanel from './components/AdminPanel';
import CandidatePanel from './components/CandidatePanel';
import QuotesCarousel from './components/QuotesCarousel';
import { Vote, LogOut, User as UserIcon, Lock, ArrowRight } from 'lucide-react';

// MOCK DATA CANDIDATES
const MOCK_CANDIDATES: CandidateData[] = [
  {
    id: '1',
    name: 'دکتر محمدی',
    username: 'drmohammadi',
    botName: '@DrMohammadiBot',
    botToken: 'token_1',
    city: 'تهران',
    province: 'تهران',
    isActive: true,
    userCount: 1250,
    slogan: 'برای آینده‌ای روشن',
    resume: 'دکتری عمران از دانشگاه تهران، ۲۰ سال سابقه اجرایی',
    address: 'تهران، میدان ونک، خیابان ملاصدرا',
    ideas: 'بهبود حمل و نقل عمومی، کاهش آلودگی هوا',
    photoUrl: 'https://picsum.photos/200/200',
    socials: {
        telegramChannel: 'https://t.me/dr_mohammadi_news',
        instagram: 'https://instagram.com/dr.mohammadi'
    },
    botConfig: {
        groupLockEnabled: true,
        lockStartTime: '23:00',
        lockEndTime: '07:00',
        blockLinks: true,
        badWords: ['توهین', 'دروغ', 'فریب']
    }
  },
  {
    id: '2',
    name: 'مهندس رضایی',
    username: 'rezaei',
    botName: '@RezaeiOfficialBot',
    botToken: 'token_2',
    city: 'اصفهان',
    province: 'اصفهان',
    isActive: false,
    userCount: 430,
    slogan: 'اصفهان، شهر زندگی',
    photoUrl: 'https://picsum.photos/201/201',
    socials: {},
    botConfig: {
        groupLockEnabled: false,
        blockLinks: false,
        badWords: []
    }
  },
  {
    id: '3',
    name: 'سارا احمدی',
    username: 'ahmadi',
    botName: '@AhmadiCampaignBot',
    botToken: 'token_3',
    city: 'شیراز',
    province: 'فارس',
    isActive: true,
    userCount: 890,
    slogan: 'جوانان، امید، تغییر',
    photoUrl: 'https://picsum.photos/202/202',
    socials: {},
    botConfig: {
        groupLockEnabled: true,
        lockStartTime: '00:00',
        lockEndTime: '06:00',
        blockLinks: true,
        badWords: []
    }
  },
  // Adding more dummy candidates for pagination test
  { id: '4', name: 'کاندید ۴', username: 'c4', botName: '@Bot4', botToken: 't4', city: 'مشهد', province: 'خراسان', isActive: true, userCount: 100 },
  { id: '5', name: 'کاندید ۵', username: 'c5', botName: '@Bot5', botToken: 't5', city: 'تبریز', province: 'آذربایجان', isActive: true, userCount: 200 },
  { id: '6', name: 'کاندید ۶', username: 'c6', botName: '@Bot6', botToken: 't6', city: 'رشت', province: 'گیلان', isActive: true, userCount: 300 },
];

// GENERATE 30 MOCK PLANS
const generatePlans = (): Plan[] => {
  const plans: Plan[] = [];
  const titles = ['پایه', 'اقتصادی', 'برنزی', 'نقره‌ای', 'طلایی', 'پلاتین', 'الماس', 'ویژه', 'VIP', 'سازمانی', 'شورای شهر', 'مجلس', 'ریاست جمهوری', 'خبرگان', 'صنفی', 'دانشجویی', 'روستایی', 'محلی', 'استانی', 'ملی', 'بین‌المللی', 'کمپین', 'تبلیغاتی', 'هوشمند', 'پیشرو', 'خلاق', 'مردمی', 'حزبی', 'ائتلافی', 'اختصاصی'];
  const colors = ['#6b7280', '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899', '#ef4444', '#06b6d4', '#84cc16', '#6366f1', '#14b8a6', '#d946ef', '#f43f5e', '#f97316', '#a855f7', '#22c55e', '#0ea5e9', '#eab308', '#84cc16', '#10b981', '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#f43f5e', '#f97316', '#f59e0b', '#84cc16', '#10b981', '#06b6d4'];

  for (let i = 0; i < 30; i++) {
    plans.push({
      id: `plan_${i + 1}`,
      title: `طرح ${titles[i]}`,
      price: `${(i + 1) * 200},000 تومان`,
      features: [
        `ویژگی شماره ۱ طرح ${titles[i]}`,
        `دسترسی به ${ (i+1) * 100 } کاربر`,
        'پشتیبانی ۲۴ ساعته',
        'پنل مدیریت پیشرفته'
      ],
      isVisible: i % 3 !== 0, // Every 3rd plan is hidden (unavailable)
      color: colors[i % colors.length]
    });
  }
  return plans;
};

const MOCK_PLANS = generatePlans();

// MOCK DATA TICKETS
const MOCK_TICKETS: Ticket[] = [
  {
    id: '101',
    candidateId: '1',
    candidateName: 'دکتر محمدی',
    subject: 'مشکل در آپلود عکس',
    status: 'ANSWERED',
    lastUpdate: Date.now(),
    messages: [
      { id: 'm1', senderId: '1', senderRole: 'CANDIDATE', text: 'سلام، عکسم آپلود نمیشه.', timestamp: Date.now() - 100000 },
      { id: 'm2', senderId: 'admin', senderRole: 'ADMIN', text: 'سلام، لطفا حجم عکس رو چک کنید باید زیر ۲ مگابایت باشه.', timestamp: Date.now() }
    ]
  }
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [candidates, setCandidates] = useState<CandidateData[]>(MOCK_CANDIDATES);
  const [plans, setPlans] = useState<Plan[]>(MOCK_PLANS);
  const [tickets, setTickets] = useState<Ticket[]>(MOCK_TICKETS);
  
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const { username, password } = loginForm;

    // Admin Check
    if (username === 'admin' && password === 'admin123') {
      setUser({ id: 'admin', username: 'admin', name: 'مدیر کل', role: 'ADMIN' });
      setError('');
      return;
    }

    // Candidate Check
    // Note: In a real app, password should be hashed. Here we check strict equality for mock.
    // Assuming mock data doesn't have password set initially, we allow login if username matches for demo purposes
    // unless a password has been set via Admin Panel.
    const candidate = candidates.find(c => c.username === username);
    
    if (candidate) {
       // Check if active
       if (!candidate.isActive) {
           setError('حساب کاربری شما توسط مدیریت غیرفعال شده است.');
           return;
       }

       // Check password (if set in mock, otherwise allow simple login for demo or default '123')
       if (candidate.password && candidate.password !== password) {
            setError('رمز عبور اشتباه است.');
            return;
       } 
       // If no password set in mock, assume '123' or allow empty (logic for demo)
       else if (!candidate.password && password !== '123') {
             // For this demo, let's assume default pass is '123' if not set
             setError('رمز عبور اشتباه است (پیش‌فرض: 123)');
             return;
       }

       setUser({ id: candidate.id, username: candidate.username, name: candidate.name, role: 'CANDIDATE' });
       setError('');
       return;
    }

    setError('نام کاربری یا رمز عبور اشتباه است');
  };

  const handleLogout = () => {
    setUser(null);
    setLoginForm({ username: '', password: '' });
  };

  const updateCandidate = (updatedData: Partial<CandidateData>) => {
     if (user?.role === 'CANDIDATE') {
         setCandidates(prev => prev.map(c => c.id === user.id ? { ...c, ...updatedData } as CandidateData : c));
     }
  };

  // Login View - MODERN SPLIT SCREEN DESIGN
  if (!user) {
    return (
      <div className="min-h-screen flex bg-gray-50">
        {/* Right Side: Login Form */}
        <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white lg:rounded-l-[3rem] shadow-2xl z-10 relative">
           <div className="w-full max-w-md space-y-8 animate-fade-in-up">
              <div className="text-center space-y-2">
                 <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-lg shadow-blue-500/30 transform rotate-3">
                    <Vote size={32} className="text-white"/>
                 </div>
                 <h1 className="text-3xl font-extrabold text-gray-800 tracking-tight">سامانه جامع انتخابات</h1>
                 <p className="text-gray-500">خوش آمدید! لطفا جهت دسترسی وارد شوید.</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-6 mt-8">
                  <div className="space-y-1">
                      <label className="text-sm font-semibold text-gray-700 mr-1">نام کاربری</label>
                      <div className="relative">
                          <UserIcon className="absolute right-3 top-3.5 text-gray-400" size={20}/>
                          <input 
                            type="text" 
                            className="w-full pr-10 pl-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition duration-200"
                            placeholder="نام کاربری خود را وارد کنید"
                            value={loginForm.username}
                            onChange={e => setLoginForm({...loginForm, username: e.target.value})}
                          />
                      </div>
                  </div>
                  <div className="space-y-1">
                      <label className="text-sm font-semibold text-gray-700 mr-1">رمز عبور</label>
                      <div className="relative">
                          <Lock className="absolute right-3 top-3.5 text-gray-400" size={20}/>
                          <input 
                            type="password" 
                            className="w-full pr-10 pl-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition duration-200"
                            placeholder="••••••••"
                            value={loginForm.password}
                            onChange={e => setLoginForm({...loginForm, password: e.target.value})}
                          />
                      </div>
                  </div>

                  {error && (
                      <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg flex items-center gap-2">
                          <span className="w-1.5 h-1.5 bg-red-600 rounded-full"></span>
                          {error}
                      </div>
                  )}

                  <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-500/30 transition duration-300 flex items-center justify-center gap-2 group">
                      ورود به سامانه
                      <ArrowRight size={20} className="group-hover:-translate-x-1 transition-transform"/>
                  </button>
              </form>

              {/* Test Credentials - Styled nicely */}
              <div className="mt-8 p-6 border border-dashed border-gray-300 rounded-xl bg-gray-50/50">
                 <p className="text-center text-xs font-bold text-gray-500 mb-4 bg-white inline-block px-3 py-1 rounded-full border mx-auto shadow-sm">داده‌های تست (برای توسعه)</p>
                 <div className="grid grid-cols-2 gap-4 text-xs text-gray-600">
                    <div className="p-2 bg-white rounded border flex flex-col items-center">
                        <span className="font-bold text-blue-600">مدیر کل</span>
                        <code className="font-mono mt-1">admin / admin123</code>
                    </div>
                    <div className="p-2 bg-white rounded border flex flex-col items-center">
                        <span className="font-bold text-green-600">کاندید نمونه</span>
                        <code className="font-mono mt-1">drmohammadi / 123</code>
                    </div>
                 </div>
              </div>
           </div>
        </div>

        {/* Left Side (LTR view: Right Side): Carousel */}
        <div className="hidden lg:block w-1/2 relative overflow-hidden">
             <QuotesCarousel />
        </div>
      </div>
    );
  }

  // App Layout
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm px-6 py-4 flex justify-between items-center z-20 sticky top-0">
        <div className="flex items-center gap-3">
           <div className="bg-blue-600 p-2 rounded-lg text-white shadow-blue-500/30 shadow-lg">
              <Vote size={24} />
           </div>
           <div>
               <h1 className="font-bold text-gray-800 text-lg hidden md:block">سامانه جامع انتخابات</h1>
               <span className="text-xs text-gray-500 md:hidden">پنل {user.role === 'ADMIN' ? 'مدیریت' : 'کاندیدا'}</span>
           </div>
        </div>
        
        <div className="flex items-center gap-4">
           <div className="flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full border border-gray-200">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600">
                 <UserIcon size={16}/>
              </div>
              <div className="flex flex-col">
                 <span className="text-sm font-bold text-gray-700">{user.name}</span>
                 <span className="text-[10px] text-gray-500">{user.role === 'ADMIN' ? 'مدیر ارشد' : 'نامزد انتخاباتی'}</span>
              </div>
           </div>
           <button 
             onClick={handleLogout} 
             className="text-gray-400 hover:text-red-600 hover:bg-red-50 transition p-2 rounded-xl"
             title="خروج از حساب"
           >
             <LogOut size={22} />
           </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden relative">
        {user.role === 'ADMIN' ? (
          <AdminPanel 
            candidates={candidates} 
            setCandidates={setCandidates}
            plans={plans}
            setPlans={setPlans}
            tickets={tickets}
            setTickets={setTickets}
          />
        ) : (
          <CandidatePanel 
            candidate={candidates.find(c => c.id === user.id)!} 
            onUpdate={updateCandidate}
            plans={plans}
            tickets={tickets}
            setTickets={setTickets}
          />
        )}
      </main>
    </div>
  );
}