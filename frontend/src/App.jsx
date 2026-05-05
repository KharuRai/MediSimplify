import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import FileUpload from './components/FileUpload';
import ResultView from './components/ResultView';
import Login from './components/Login';
import Signup from './components/Signup';
import Dashboard from './components/Dashboard';
import { AuthProvider, useAuth } from './contexts/AuthContext';

function PrivateRoute({ children }) {
  const { session } = useAuth();
  return session ? children : <Navigate to="/login" />;
}

function Header({ theme, toggleTheme }) {
  const { session, signOut } = useAuth();
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-700 py-4 px-6 md:px-12 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shadow-md">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-700 to-primary-500">
            MediSimplify
          </h1>
        </Link>
        <div className="flex items-center gap-4">
          <button
            onClick={toggleTheme}
            className="inline-flex items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 w-10 h-10 hover:bg-gray-100 dark:hover:bg-slate-700 transition"
            aria-label={theme === 'dark' ? 'Current theme: dark' : 'Current theme: light'}
          >
            {theme === 'dark' ? '🌙' : '☀️'}
          </button>
          {session && (
            <div className="flex items-center gap-4 text-sm font-medium">
              <Link to="/dashboard" className="text-gray-600 hover:text-primary-600 dark:text-slate-200 dark:hover:text-primary-400">History</Link>
              <button onClick={signOut} className="text-gray-600 hover:text-red-600 dark:text-slate-200">Sign Out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function MainApp() {
  const [result, setResult] = useState(null);

  return (
    <main className="flex-grow flex items-center justify-center p-6 py-12 md:py-20">
      <div className="w-full relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-[500px] bg-primary-200/30 blur-[100px] rounded-full pointer-events-none"></div>
        <div className="relative z-10">
          {!result ? (
            <FileUpload onUploadSuccess={setResult} />
          ) : (
            <ResultView result={result} onBack={() => setResult(null)} />
          )}
        </div>
      </div>
    </main>
  );
}

function App() {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const storedTheme = window.localStorage.getItem('theme');
    if (storedTheme === 'dark' || storedTheme === 'light') {
      setTheme(storedTheme);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark');
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.remove('dark');
    document.body.classList.remove('dark');
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.body.classList.add('dark');
    }
    window.localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((value) => (value === 'dark' ? 'light' : 'dark'));

  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 dark:text-slate-100 flex flex-col font-sans">
          <Header theme={theme} toggleTheme={toggleTheme} />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
            <Route path="/" element={<PrivateRoute><MainApp /></PrivateRoute>} />
          </Routes>
          <footer className="py-6 text-center text-sm text-gray-500 dark:text-slate-400">
            <p>© 2026 MediSimplify. AI-Powered Medical Report Simplifier.</p>
          </footer>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
