import React from 'react';
import { Download, ArrowLeft, AlertTriangle, Info, Pill, FileText } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function ResultView({ result, onBack }) {
  const { data, id } = result;
  const { session } = useAuth();

  const handleDownload = async () => {
    if (!session) return;
    try {
      const response = await fetch(`http://localhost:8000/reports/${id}/download`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });
      if (!response.ok) throw new Error('Failed to get download link');
      const resData = await response.json();
      window.open(resData.signed_url, '_blank');
    } catch (err) {
      alert('Error downloading: ' + err.message);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 lg:p-8 bg-white rounded-3xl shadow-2xl border border-gray-100 transition-all duration-500 ease-in-out animate-in fade-in slide-in-from-bottom-4">
      
      <div className="flex items-center justify-between mb-8 pb-6 border-b border-gray-100">
        <button 
          onClick={onBack}
          className="flex items-center text-gray-500 hover:text-primary-600 transition-colors font-medium"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Upload
        </button>
        
        <button 
          onClick={handleDownload}
          className="flex items-center px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-md text-sm font-medium"
        >
          <Download className="w-4 h-4 mr-2" />
          Download PDF
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Column: Primary Info */}
        <div className="space-y-6">
          <div className="bg-blue-50/50 p-6 rounded-2xl border border-blue-100">
            <div className="flex items-center text-blue-800 font-semibold text-lg mb-3">
              <Pill className="w-5 h-5 mr-2" />
              Medicines Identified
            </div>
            <ul className="space-y-2">
              {data?.Medicines && data.Medicines.length > 0 ? (
                data.Medicines.map((med, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 mr-2 flex-shrink-0"></span>
                    <span className="text-gray-700">{med}</span>
                  </li>
                ))
              ) : (
                <p className="text-gray-500 italic">No specific medicines found.</p>
              )}
            </ul>
          </div>

          <div className="bg-emerald-50/50 p-6 rounded-2xl border border-emerald-100">
            <div className="flex items-center text-emerald-800 font-semibold text-lg mb-3">
              <Info className="w-5 h-5 mr-2" />
              Purpose
            </div>
            <p className="text-gray-700 leading-relaxed">
              {data?.Purpose || "No purpose specified."}
            </p>
          </div>
        </div>

        {/* Right Column: Secondary Info */}
        <div className="space-y-6">
          <div className="bg-amber-50/50 p-6 rounded-2xl border border-amber-100">
            <div className="flex items-center text-amber-800 font-semibold text-lg mb-3">
              <FileText className="w-5 h-5 mr-2" />
              Dosage Instructions
            </div>
            <p className="text-gray-700 leading-relaxed">
              {data?.Dosage || "No dosage instructions found."}
            </p>
          </div>

          <div className="bg-red-50/50 p-6 rounded-2xl border border-red-100">
            <div className="flex items-center text-red-800 font-semibold text-lg mb-3">
              <AlertTriangle className="w-5 h-5 mr-2" />
              Warnings & Side Effects
            </div>
            <ul className="space-y-2">
              {data?.Warnings && data.Warnings.length > 0 ? (
                data.Warnings.map((warning, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 mt-2 mr-2 flex-shrink-0"></span>
                    <span className="text-gray-700">{warning}</span>
                  </li>
                ))
              ) : (
                <p className="text-gray-500 italic">No specific warnings found.</p>
              )}
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-gray-100">
        <div className="flex items-start text-xs text-gray-400 bg-gray-50 p-4 rounded-lg">
          <Info className="w-4 h-4 mr-2 flex-shrink-0 mt-0.5" />
          <p>{data?.Disclaimer || "This is an AI generated summary. Please consult a medical professional for advice."}</p>
        </div>
      </div>
    </div>
  );
}
