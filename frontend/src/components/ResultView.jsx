import React from 'react';
import { Download, ArrowLeft, Info, FileText, Activity } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiUrl } from '../config';

export default function ResultView({ result, onBack }) {
  const { data, id } = result;
  const { session } = useAuth();

  const handleDownload = async () => {
    if (!session) return;
    try {
      const response = await fetch(apiUrl(`/reports/${id}/download`), {
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

  const renderValue = (key, value) => {
    if (!value) return null;

    if (typeof value === 'string') {
      return <p className="text-gray-700 leading-relaxed">{value}</p>;
    }

    if (Array.isArray(value) && value.length > 0) {
      if (typeof value[0] === 'object') {
        const isMedicineList = value.some((item) =>
          item && (item.name || item.dosage || item.frequency || item.purpose || item.warnings || item.fda_validation)
        );

        if (isMedicineList) {
          return (
            <div className="space-y-4">
              {value.map((item, idx) => (
                <div key={idx} className="p-4 rounded-xl border bg-white dark:bg-slate-900 border-gray-100 dark:border-slate-700">
                  <div className="font-semibold text-gray-800 mb-2">{item.name || "Unknown Medicine"}</div>
                  {item.dosage && <p className="text-sm text-gray-600 mb-1"><span className="font-medium">Dosage:</span> {item.dosage}</p>}
                  {item.frequency && <p className="text-sm text-gray-600 mb-1"><span className="font-medium">How to take:</span> {item.frequency}</p>}
                  {item.purpose && <p className="text-sm text-gray-600 mb-1"><span className="font-medium">Use:</span> {item.purpose}</p>}
                  {item.warnings && <p className="text-sm text-amber-700 mb-1"><span className="font-medium">Warnings:</span> {item.warnings}</p>}
                  {item.fda_validation && (
                    <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="text-sm font-medium text-blue-800 mb-1">FDA Information:</div>
                      <div className="text-sm text-blue-700">{item.fda_validation}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          );
        }

        // Special rendering for arrays of objects (like Lab Results)
        return (
          <div className="space-y-4">
            {value.map((item, idx) => (
              <div 
                key={idx} 
                className={`p-4 rounded-xl border ${
                      item.status_report_based === 'High' ? 'bg-red-50 border-red-200' :
                      item.status_report_based === 'Low' ? 'bg-amber-50 border-amber-200' :
                        'bg-white dark:bg-slate-900 border-gray-100 dark:border-slate-700'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="font-semibold text-gray-800">{item.test_name || "Unknown Test"}</span>
                  {item.status_report_based && item.status_report_based !== 'Unknown' && item.status_report_based !== 'Normal' && (
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      item.status_report_based === 'High' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {item.status_report_based}
                    </span>
                  )}
                  {item.status_report_based === 'Normal' && (
                    <span className="text-xs px-2 py-1 rounded-full font-medium bg-emerald-100 text-emerald-700">
                      Normal
                    </span>
                  )}
                </div>
                <div className="flex items-center text-sm text-gray-600 mb-2">
                  <span className="font-medium mr-2">{item.value !== null ? item.value : 'N/A'} {item.unit || ''}</span>
                  {(item.report_range || item.min_range || item.max_range) && (
                    <span className="text-gray-400 text-xs">
                      (Report: {item.report_range || `${item.min_range || '?'} - ${item.max_range || '?'}`})
                    </span>
                  )}
                </div>
                {item.clinical_range && (
                  <div className="text-sm text-gray-500 dark:text-slate-400 mb-2">
                    <span className="font-medium">Clinical Ref:</span> {item.clinical_range}
                  </div>
                )}
                {item.status_clinical && item.status_clinical !== 'Unknown' && (
                  <div className="text-sm text-gray-500 dark:text-slate-400 mb-2">
                    <span className="font-medium">Status (Clinical):</span> {item.status_clinical}
                  </div>
                )}
                {item.confidence && (
                  <div className="inline-flex items-center gap-2 text-sm font-medium mb-2">
                    <span className={`px-2 py-1 rounded-full ${
                      item.confidence === 'High' ? 'bg-emerald-100 text-emerald-700' :
                      item.confidence === 'Medium' ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      Confidence: {item.confidence}
                    </span>
                  </div>
                )}
                {item.warning && (
                  <div className="text-xs text-amber-700 border border-amber-100 rounded-xl p-3 mb-2 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700">
                    {item.warning}
                  </div>
                )}
                {item.explanation && (
                  <p className="text-sm text-gray-500 dark:text-slate-400 mt-2 border-t border-gray-100 dark:border-slate-700 pt-2">{item.explanation}</p>
                )}
              </div>
            ))}
          </div>
        );
      } else {
        // Simple string array
        return (
          <ul className="space-y-2">
            {value.map((item, idx) => (
              <li key={idx} className="flex items-start">
                <span className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-2 mr-2 flex-shrink-0"></span>
                <span className="text-gray-700 dark:text-slate-200">{item}</span>
              </li>
            ))}
          </ul>
        );
      }
    }
    
    return <p className="text-gray-700 dark:text-slate-200">{String(value)}</p>;
  };

  return (
    <div className={`w-full ${result.image_urls && result.image_urls.length > 0 ? 'max-w-7xl' : 'max-w-4xl'} mx-auto p-6 lg:p-8 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-gray-100 dark:border-slate-700 transition-all duration-500 ease-in-out animate-in fade-in slide-in-from-bottom-4`}>
      
      <div className="flex items-center justify-between mb-8 pb-6 border-b border-gray-100 dark:border-slate-700">
        <button 
          onClick={onBack}
          className="flex items-center text-gray-500 dark:text-slate-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors font-medium"
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

      <div className={`grid grid-cols-1 ${result.image_urls && result.image_urls.length > 0 ? 'lg:grid-cols-2 gap-8' : ''}`}>
        
        {/* Left Column: AI Summary */}
        <div className="space-y-6">
          {Object.entries(data || {}).map(([key, value]) => {
            if (key === 'Disclaimer' || key === 'source_image_paths' || !value || (Array.isArray(value) && value.length === 0)) return null;
            
            return (
              <div key={key} className="bg-slate-50 dark:bg-slate-900 p-6 rounded-2xl border border-slate-100 dark:border-slate-700">
                <div className="flex items-center text-slate-800 font-semibold text-lg mb-4 capitalize">
                  <FileText className="w-5 h-5 mr-2 text-primary-500" />
                  {key}
                </div>
                {renderValue(key, value)}
              </div>
            );
          })}
          
          <div className="mt-8 pt-6 border-t border-gray-100 dark:border-slate-700">
            <div className="flex items-start text-xs text-gray-400 dark:text-slate-400 bg-gray-50 dark:bg-slate-800 p-4 rounded-lg">
              <Info className="w-4 h-4 mr-2 flex-shrink-0 mt-0.5" />
              <p>{data?.Disclaimer || "This is an AI generated summary. Please consult a medical professional for advice."}</p>
            </div>
          </div>
        </div>

        {/* Right Column: Source Document Images */}
        {result.image_urls && result.image_urls.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-xl font-bold text-slate-800 dark:text-slate-100 border-b border-slate-100 dark:border-slate-700 pb-2 flex items-center">
              Source Document
            </h3>
            <div className="flex flex-col space-y-4 bg-slate-50 dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-y-auto max-h-[800px] shadow-inner">
              {result.image_urls.map((url, idx) => (
                <div key={idx} className="relative group">
                  <span className="absolute top-2 left-2 bg-slate-900/70 text-white text-xs px-2 py-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity">
                    Page {idx + 1}
                  </span>
                  <img 
                    src={url} 
                    alt={`Original document page ${idx + 1}`} 
                    className="w-full h-auto rounded-xl shadow-sm border border-slate-300"
                    loading="lazy"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
