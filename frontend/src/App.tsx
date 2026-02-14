import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Login from './components/Login';
import AdminPanel from './components/admin/AdminPanel';
import CandidatePanel from './components/candidate/CandidatePanel';
import { api } from './services/api';
import { User, CandidateData, Plan, Ticket } from './types';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [loading, setLoading] = useState(true);

  // Data state
  const [candidates, setCandidates] = useState<CandidateData[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [candidate, setCandidate] = useState<CandidateData | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      if (storedToken) {
        try {
          const userData = await api.getMe(storedToken);
          setUser(userData);
          setToken(storedToken);
        } catch (e) {
          console.error("Auth failed", e);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      if (!user || !token) return;

      try {
        if (user.role === 'ADMIN') {
          // Fetch independently to avoid one failure blocking all
          api.getCandidates(token).then(setCandidates).catch(e => console.error("Candidates fetch failed", e));
          api.getPlans().then(setPlans).catch(e => console.error("Plans fetch failed", e));
          api.getTickets().then(setTickets).catch(e => console.error("Tickets fetch failed", e));
        } else if (user.role === 'CANDIDATE') {
          // For candidate, we need to find their candidate profile
          api.getCandidates(token).then(allCandidates => {
            const me = allCandidates.find(c => c.id === user.id);
            if (me) setCandidate(me);
          }).catch(e => console.error("Candidate profile fetch failed", e));

          api.getPlans().then(setPlans).catch(e => console.error("Plans fetch failed", e));
          api.getTickets().then(setTickets).catch(e => console.error("Tickets fetch failed", e));
        }
      } catch (e) {
        console.error("Data fetch setup failed", e);
      }
    };

    if (!loading && user) {
      let intervalId: any = null;

      const startPolling = () => {
        if (intervalId) return;
        // Initial fetch when polling starts/resumes
        fetchData();
        intervalId = setInterval(fetchData, 15000);
      };

      const stopPolling = () => {
        if (!intervalId) return;
        clearInterval(intervalId);
        intervalId = null;
      };

      const onVisibilityChange = () => {
        try {
          if (typeof document !== 'undefined' && document.hidden) stopPolling();
          else startPolling();
        } catch {
          // If document is not available, keep polling.
          startPolling();
        }
      };

      // Start polling only when tab is visible.
      onVisibilityChange();
      document.addEventListener('visibilitychange', onVisibilityChange);

      return () => {
        stopPolling();
        document.removeEventListener('visibilitychange', onVisibilityChange);
      };
    }
  }, [user, token, loading]);

  const handleLogin = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    navigate('/');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setUser(null);
    setCandidates([]);
    setPlans([]);
    setTickets([]);
    setCandidate(null);
    navigate('/login');
  };

  const pickCandidateUpdatePayload = (updated: Partial<CandidateData> & Record<string, any>) => {
    const payload: Record<string, any> = {};

    const map: Array<[string, string]> = [
      ['name', 'name'],
      ['full_name', 'name'],
      ['username', 'username'],
      ['phone', 'phone'],
      ['bot_name', 'bot_name'],
      ['botName', 'bot_name'],
      ['bot_token', 'bot_token'],
      ['botToken', 'bot_token'],
      ['slogan', 'slogan'],
      ['bio', 'bio'],
      ['city', 'city'],
      ['province', 'province'],
      ['constituency', 'constituency'],
      ['image_url', 'image_url'],
      ['resume', 'resume'],
      ['ideas', 'ideas'],
      ['address', 'address'],
      ['voice_url', 'voice_url'],
      ['socials', 'socials'],
      ['bot_config', 'bot_config'],
      ['is_active', 'is_active'],
      ['isActive', 'is_active'],
      ['password', 'password'],
    ];

    for (const [fromKey, toKey] of map) {
      if (Object.prototype.hasOwnProperty.call(updated, fromKey)) {
        const value = (updated as any)[fromKey];
        if (value !== undefined) payload[toKey] = value;
      }
    }

    // Never allow mutating identity/readonly fields from candidate panel.
    delete payload.id;
    delete payload.role;
    delete payload.vote_count;
    delete payload.created_at_jalali;
    delete payload.active_plan_id;
    delete payload.plan_start_date;
    delete payload.plan_expires_at;

    return payload;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <div className="animate-spin w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto"></div>
          <p className="text-gray-600">در حال بارگذاری...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" replace />} />

      <Route path="/" element={
        user ? (
          user.role === 'ADMIN' ? (
            <AdminPanel
              candidates={candidates}
              setCandidates={setCandidates}
              plans={plans}
              setPlans={setPlans}
              tickets={tickets}
              setTickets={setTickets}
              onLogout={handleLogout}
            />
          ) : (
            candidate ? (
              <CandidatePanel
                candidate={candidate}
                onUpdate={async (updated) => {
                  if (!user || !token) {
                    throw new Error('ابتدا وارد حساب کاربری شوید.');
                  }
                  const payload = pickCandidateUpdatePayload(updated as any);
                  const saved = await api.updateCandidate(parseInt(String(user.id)), payload, token);
                  setCandidate(saved as any);
                }}
                plans={plans}
                tickets={tickets}
                setTickets={setTickets}
                onLogout={handleLogout}
              />
            ) : (
              <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                  <p>پروفایل کاندیدا یافت نشد.</p>
                  <button onClick={handleLogout} className="mt-4 text-blue-600">خروج</button>
                </div>
              </div>
            )
          )
        ) : (
          <Navigate to="/login" replace />
        )
      } />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
