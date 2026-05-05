import React, { useState } from 'react';
import { UploadCloud, File, X, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiUrl } from '../config';

export default function FileUpload({ onUploadSuccess }) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [reportType, setReportType] = useState('prescription');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { session } = useAuth();

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
       const validTypes = ['application/pdf'];
      if (validTypes.includes(droppedFile.type)) {
        setFile(droppedFile);
        setError('');
      } else {
         setError('Please upload a valid PDF file.');
      }
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
       const validTypes = ['application/pdf'];
      if (validTypes.includes(selectedFile.type)) {
        setFile(selectedFile);
        setError('');
      } else {
         setError('Please upload a valid PDF file.');
      }
    }
  };

  const handleUpload = async () => {
    if (!file || !session) return;
    
    setLoading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('report_type', reportType);
    
    try {
      const response = await fetch(apiUrl('/upload'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload failed');
      }
      
      const data = await response.json();
      onUploadSuccess(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto p-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Simplify Medical Report</h2>
        <p className="text-gray-500 dark:text-slate-400 mt-2">Upload your complex medical PDF or Image to get a clear, simplified summary.</p>
      </div>

      {!file ? (
        <div 
          className={`relative flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-xl transition-colors
            ${dragActive ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 hover:border-primary-400 bg-gray-50 dark:border-slate-700 dark:hover:border-primary-400 dark:bg-slate-800'}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
             accept=".pdf"
            onChange={handleChange}
          />
          <UploadCloud className={`w-16 h-16 mb-4 ${dragActive ? 'text-primary-600' : 'text-gray-400 dark:text-slate-400'}`} />
           <p className="text-lg font-medium text-slate-900 dark:text-slate-100">Drag & drop your PDF here</p>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">or click to browse files</p>
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-100 dark:border-primary-700">
          <div className="flex items-center space-x-3">
            <File className="w-8 h-8 text-primary-600" />
            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate max-w-xs">{file.name}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
          <button 
            onClick={() => setFile(null)}
            className="p-1 hover:bg-primary-100 rounded-full transition-colors"
            disabled={loading}
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-100">
          {error}
        </div>
      )}

      {/* Report Type Selector */}
      <div className="mt-6 mb-2 text-left">
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-2">Select Report Type</label>
        <select 
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          className="w-full p-3 border border-gray-300 rounded-lg bg-white text-slate-900 focus:ring-primary-500 focus:border-primary-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        >
          <option value="prescription">Prescription</option>
          <option value="lab">Lab Report</option>
          <option value="ecg">ECG / EKG</option>
          <option value="general">General Diagnosis Report</option>
        </select>
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className={`w-full mt-6 py-3 px-4 rounded-xl font-medium text-white flex justify-center items-center space-x-2 transition-all
          ${(!file || loading) ? 'bg-gray-300 cursor-not-allowed dark:bg-slate-700 dark:text-slate-200' : 'bg-primary-600 hover:bg-primary-700 shadow-md hover:shadow-lg'}`}
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Processing with AI... This might take a minute.</span>
          </>
        ) : (
          <span>Simplify Report</span>
        )}
      </button>
    </div>
  );
}
