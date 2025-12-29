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
          const [cData, pData, tData] = await Promise.all([
            api.getCandidates(),
            api.getPlans(),
            api.getTickets()
          ]);
          setCandidates(cData);
          setPlans(pData);
          setTickets(tData);
        } else if (user.role === 'CANDIDATE') {
          // For candidate, we need to find their candidate profile
          const allCandidates = await api.getCandidates();
          const me = allCandidates.find(c => c.user_id === parseInt(user.id));
          if (me) setCandidate(me);

          const [pData, tData] = await Promise.all([
            api.getPlans(),
            api.getTickets()
          ]);
          setPlans(pData);
          setTickets(tData); // Filtered in component usually, or here
        }
      } catch (e) {
        console.error("Data fetch failed", e);
      }
    };

    if (!loading && user) {
      fetchData();
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
                onUpdate={(updated) => setCandidate(prev => prev ? ({ ...prev, ...updated }) : null)}
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
