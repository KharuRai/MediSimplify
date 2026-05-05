import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    if (password !== passwordConfirm) {
      return setError('Passwords do not match');
    }
    try {
      setError('');
      setLoading(true);
      const { error } = await signUp({ email, password });
      if (error) throw error;
      navigate('/');
    } catch (err) {
      setError('Failed to create an account: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="bg-white dark:bg-slate-900 p-8 rounded-xl shadow-lg w-full max-w-md border border-gray-100 dark:border-slate-700">
        <h2 className="text-2xl font-bold text-center mb-6">Sign Up for MediSimplify</h2>
        {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Email</label>
            <input 
              type="email" 
              required 
              className="mt-1 w-full p-2 border border-gray-300 rounded bg-white text-slate-900 focus:ring-primary-500 focus:border-primary-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Password</label>
            <input 
              type="password" 
              required 
              className="mt-1 w-full p-2 border border-gray-300 rounded bg-white text-slate-900 focus:ring-primary-500 focus:border-primary-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Confirm Password</label>
            <input 
              type="password" 
              required 
              className="mt-1 w-full p-2 border border-gray-300 rounded bg-white text-slate-900 focus:ring-primary-500 focus:border-primary-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" 
              value={passwordConfirm} 
              onChange={(e) => setPasswordConfirm(e.target.value)} 
            />
          </div>
          <button 
            disabled={loading} 
            type="submit" 
            className="w-full bg-primary-600 text-white p-2 rounded hover:bg-primary-700 disabled:opacity-50"
          >
            Sign Up
          </button>
        </form>
        <div className="mt-4 text-center text-sm">
          Already have an account? <Link to="/login" className="text-primary-600 hover:underline">Log In</Link>
        </div>
      </div>
    </div>
  );
}
