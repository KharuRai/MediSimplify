import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import ResultView from './components/ResultView';

function App() {
  const [result, setResult] = useState(null);

  const handleUploadSuccess = (data) => {
    setResult(data);
  };

  const handleBack = () => {
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <header className="bg-white border-b border-gray-200 py-4 px-6 md:px-12 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center shadow-md">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-700 to-primary-500">
              MediSimplify
            </h1>
          </div>
        </div>
      </header>

      <main className="flex-grow flex items-center justify-center p-6 py-12 md:py-20">
        <div className="w-full relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-[500px] bg-primary-200/30 blur-[100px] rounded-full pointer-events-none"></div>
          
          <div className="relative z-10">
            {!result ? (
              <FileUpload onUploadSuccess={handleUploadSuccess} />
            ) : (
              <ResultView result={result} onBack={handleBack} />
            )}
          </div>
        </div>
      </main>

      <footer className="py-6 text-center text-sm text-gray-500">
        <p>© 2026 MediSimplify. AI-Powered Medical Report Simplifier.</p>
      </footer>
    </div>
  );
}

export default App;
