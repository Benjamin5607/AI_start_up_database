import React, { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';

function App() {
  const [currentStep, setCurrentStep] = useState(0); // 진행 단계 상태
  const [reportData, setReportData] = useState({}); // 보고서 데이터 상태
  const [isGenerating, setIsGenerating] = useState(false); // 보고서 생성 중 상태
  const steps = ['Data Collection', 'Data Analysis', 'Final Report']; // 진행 단계 배열

  useEffect(() => {
    // 로컬 스토리지에서 이전 진행 상태 로드
    const storedStep = localStorage.getItem('currentStep');
    if (storedStep) {
      setCurrentStep(parseInt(storedStep));
    }
  }, []);

  useEffect(() => {
    // 진행 상태 로컬 스토리지에 저장
    localStorage.setItem('currentStep', currentStep.toString());
  }, [currentStep]);

  const handleGenerateReport = () => {
    setIsGenerating(true);
    // **예시: 실제 보고서 생성 로직 추가 (2초 대기)**
    setTimeout(() => {
      setReportData({ title: 'Final Report', content: 'This is your final report.' });
      setIsGenerating(false);
    }, 2000);
  };

  const handlePreviousStep = () => {
    if (currentStep > 0) {
      setCurrentStep((prevStep) => prevStep - 1);
    }
  };

  return (
    <div className="flex flex-col h-screen justify-center items-center bg-gray-100">
      <header className="bg-blue-500 text-white p-4 mb-4">
        <h2>AI Start Up Database Project</h2>
        <p>Current Step: {steps[currentStep]}</p>
      </header>
      <main className="container mx-auto p-4">
        {currentStep < steps.length - 1 && (
          <div>
            <p>Progress: {currentStep + 1}/{steps.length}</p>
            <button
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
              onClick={handleGenerateReport}
            >
              {isGenerating ? 'Generating...' : 'Proceed to Next Step'}
            </button>
          </div>
        )}
        {currentStep === steps.length - 1 && (
          <div>
            <h3>Final Report Preview</h3>
            <div className="bg-white p-4 shadow-md">
              <h4>{reportData.title}</h4>
              <p>{reportData.content}</p>
              <button
                className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
                onClick={handleGenerateReport}
              >
                {isGenerating ? 'Generating Final Report...' : 'Generate Final Report'}
              </button>
            </div>
            <button
              className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded mt-4"
              onClick={handlePreviousStep}
            >
              <ArrowLeft size={20} className="mr-2" /> Back to Previous Step
            </button>
          </div>
        )}
      </main>
      <footer className="bg-gray-200 text-gray-600 p-4 mt-auto">
        <p>&copy; 2023 AI Start Up</p>
      </footer>
    </div>
  );
}

export default App;
