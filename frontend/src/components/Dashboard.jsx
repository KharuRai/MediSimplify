import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../supabaseClient';
import { apiUrl } from '../config';

export default function Dashboard() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { session } = useAuth();

  useEffect(() => {
    async function fetchReports() {
      try {
        if (!session) return;
        const response = await fetch(apiUrl('/reports'), {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        });
        if (!response.ok) throw new Error('Failed to fetch reports');
        const data = await response.json();
        setReports(data.reports || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchReports();
  }, [session]);

  const handleDownload = async (reportId) => {
    try {
      const response = await fetch(apiUrl(`/reports/${reportId}/download`), {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });
      if (!response.ok) throw new Error('Failed to get download link');
      const data = await response.json();
      window.open(data.signed_url, '_blank');
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading) return <div className="text-center p-8 text-slate-900 dark:text-slate-100">Loading your history...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 text-slate-900 dark:text-slate-100">
      <h2 className="text-2xl font-bold mb-6">Your Medical Reports</h2>
      {error && <div className="bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 p-3 rounded mb-4">{error}</div>}
      
      {reports.length === 0 ? (
        <p className="text-gray-500 dark:text-slate-300 bg-white dark:bg-slate-900 p-8 rounded-xl shadow text-center">No reports found. Upload a PDF to get started!</p>
      ) : (
        <div className="bg-white dark:bg-slate-900 shadow rounded-xl overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
            <thead className="bg-gray-50 dark:bg-slate-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">File Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-slate-950 divide-y divide-gray-200 dark:divide-slate-700">
              {reports.map((report) => (
                <tr key={report.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-slate-300">
                    {new Date(report.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-slate-100">
                    {report.original_filename}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-slate-300">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                      ${report.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/60 dark:text-green-200' : 
                        report.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/60 dark:text-red-200' : 
                        'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/60 dark:text-yellow-200'}`}>
                      {report.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-slate-300">
                    {report.status === 'completed' && (
                      <button 
                        onClick={() => handleDownload(report.id)}
                        className="text-primary-600 hover:text-primary-900 font-medium"
                      >
                        Download PDF
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
