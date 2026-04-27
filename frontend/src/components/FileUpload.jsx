import React, { useState } from 'react';
import { UploadCloud, File, X, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function FileUpload({ onUploadSuccess }) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
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
      if (droppedFile.type === 'application/pdf') {
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
      if (selectedFile.type === 'application/pdf') {
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
    
    try {
      const response = await fetch('http://localhost:8000/upload', {
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
    <div className="w-full max-w-xl mx-auto p-6 bg-white rounded-2xl shadow-xl border border-gray-100">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Simplify Medical Report</h2>
        <p className="text-gray-500 mt-2">Upload your complex medical PDF to get a clear, simplified summary.</p>
      </div>

      {!file ? (
        <div 
          className={`relative flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-xl transition-colors
            ${dragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-primary-400 bg-gray-50'}`}
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
          <UploadCloud className={`w-16 h-16 mb-4 ${dragActive ? 'text-primary-600' : 'text-gray-400'}`} />
          <p className="text-lg font-medium text-gray-700">Drag & drop your PDF here</p>
          <p className="text-sm text-gray-500 mt-1">or click to browse files</p>
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 bg-primary-50 rounded-lg border border-primary-100">
          <div className="flex items-center space-x-3">
            <File className="w-8 h-8 text-primary-600" />
            <div>
              <p className="text-sm font-medium text-gray-800 truncate max-w-xs">{file.name}</p>
              <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
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

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className={`w-full mt-6 py-3 px-4 rounded-xl font-medium text-white flex justify-center items-center space-x-2 transition-all
          ${(!file || loading) ? 'bg-gray-300 cursor-not-allowed' : 'bg-primary-600 hover:bg-primary-700 shadow-md hover:shadow-lg'}`}
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
