import React, { useState, useEffect } from 'react';
import { ArrowLeft, Plus, Download, Share } from 'lucide-react';

function App() {
  const [currentStep, setCurrentStep] = useState(0); // **진행 단계 상태**
  const [reportData, setReportData] = useState({}); // **보고서 데이터 상태**
  const [isGenerating, setIsGenerating] = useState(false); // **보고서 생성 중 상태**
  const [error, setError] = useState(null); // **에러 상태**
  const [inputData, setInputData] = useState({ title: '', content: '' }); // **입력 데이터 상태**
  const [savedReports, setSavedReports] = useState([]); // **저장된 보고서 목록**
  const [copied, setCopied] = useState(false); // **복사 상태**
  const [toolLink, setToolLink] = useState(''); // **외부 툴 링크**

  // **이전 단계로 이동**
  const handlePreviousStep = () => {
    if (currentStep > 0) {
      setCurrentStep((prevStep) => prevStep - 1);
    }
  };

  // **다음 단계로 이동 (예시: 3단계 가정)**
  const handleNextStep = () => {
    if (currentStep < 3) { // **단계 수 조정 (추가 단계 포함)**
      setCurrentStep((prevStep) => prevStep + 1);
    }
  };

  // **입력 데이터 업데이트**
  const handleInputUpdate = (e) => {
    setInputData({ ...inputData, [e.target.name]: e.target.value });
  };

  // **보고서 생성**
  const handleGenerateReport = () => {
    setIsGenerating(true);
    try {
      // **실제 보고서 생성 로직 (예시)**
      const generatedData = { ...inputData, timestamp: new Date().toISOString() };
      setReportData(generatedData);
      setTimeout(() => { // **로딩 시뮬레이션**
        setIsGenerating(false);
      }, 2000);
    } catch (error) {
      setError(error.message);
      setIsGenerating(false);
    }
  };

  // **보고서 저장**
  const handleSaveReport = () => {
    if (Object.keys(reportData).length > 0) {
      setSavedReports([...savedReports, { ...reportData, id: Date.now() }]);
      alert('Report Saved!');
    }
  };

  // **보고서 복사**
  const handleCopyReport = () => {
    if (Object.keys(reportData).length > 0) {
      navigator.clipboard.writeText(JSON.stringify(reportData, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // **외부 툴 링크 생성**
  const handleGenerateToolLink = () => {
    if (Object.keys(reportData).length > 0) {
      setToolLink(`https://example.com/tool?data=${encodeURIComponent(JSON.stringify(reportData))}`);
    }
  };

  // **자동 다음 단계 이동 (예시: 보고서 생성 후)**
  useEffect(() => {
    if (Object.keys(reportData).length > 0 && currentStep === 2) {
      setTimeout(() => { // **자동 진행 시뮬레이션**
        handleNextStep();
      }, 3000);
    }
  }, [reportData, currentStep]);

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100">
      <header className="bg-blue-500 p-4 text-white rounded-lg mb-4">
        <p className="text-2xl font-bold">AI Start Up Database Project</p>
        <p className="text-lg mt-2">Current Step: {['Introduction', 'Data Input', 'Report Generation', 'Report Actions'][currentStep]}</p>
      </header>
      {currentStep === 0 && ( // **소개 단계**
        <div className="p-4 bg-white rounded-lg mb-4">
          <h3 className="text-lg font-bold mb-2">Welcome</h3>
          <p>Start your report generation journey here.</p>
          <button onClick={handleNextStep} className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
            Next <ArrowLeft size={20} className="ml-2 rotate-180" />
          </button>
        </div>
      )}
      {currentStep === 1 && ( // **데이터 입력 단계**
        <div className="p-4 bg-white rounded-lg mb-4">
          <h3 className="text-lg font-bold mb-2">Input Your Data</h3>
          <input
            type="text"
            name="title"
            value={inputData.title}
            onChange={handleInputUpdate}
            placeholder="Report Title"
            className="w-full p-2 mb-2 border border-gray-300 rounded"
          />
          <textarea
            name="content"
            value={inputData.content}
            onChange={handleInputUpdate}
            placeholder="Report Content"
            className="w-full p-2 mb-4 border border-gray-300 rounded"
          />
          <div className="flex justify-between">
            <button onClick={handlePreviousStep} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded">
              <ArrowLeft size={20} className="mr-2" /> Previous
            </button>
            <button onClick={handleNextStep} className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
              Next <ArrowLeft size={20} className="ml-2 rotate-180" />
            </button>
          </div>
        </div>
      )}
      {currentStep === 2 && ( // **보고서 생성 단계**
        <div className="p-4 bg-white rounded-lg mb-4">
          <h3 className="text-lg font-bold mb-2">Generate Report</h3>
          <button
            onClick={handleGenerateReport}
            className={`bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded ${isGenerating ? 'opacity-50 cursor-not-allowed' : ''}`}
            disabled={isGenerating}
          >
            {isGenerating ? 'Generating...' : 'Generate Report'}
          </button>
          {error && (
            <div className="bg-red-500 text-white p-2 rounded mt-4">
              Error: {error}
            </div>
          )}
          <div className="flex justify-between mt-4">
            <button onClick={handlePreviousStep} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded">
              <ArrowLeft size={20} className="mr-2" /> Previous
            </button>
            {Object.keys(reportData).length > 0 && (
              <button onClick={handleNextStep} className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
                Next <ArrowLeft size={20} className="ml-2 rotate-180" />
              </button>
            )}
          </div>
        </div>
      )}
      {currentStep === 3 && ( // **보고서 액션 단계**
        <div className="p-4 bg-white rounded-lg mb-4">
          <h3 className="text-lg font-bold mb-2">Report Actions</h3>
          {Object.keys(reportData).length > 0 && (
            <div>
              <div className="bg-green-200 p-4 rounded mb-4">
                <h4 className="text-lg font-bold mb-2">Generated Report</h4>
                <p><strong>Title:</strong> {reportData.title}</p>
                <p><strong>Content:</strong> {reportData.content}</p>
                <p><strong>Timestamp:</strong> {reportData.timestamp}</p>
              </div>
              <button onClick={handleSaveReport} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mr-2">
                Save <Plus size={20} className="ml-2" />
              </button>
              <button onClick={handleCopyReport} className={`bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded mr-2 ${copied ? 'opacity-50' : ''}`}
                disabled={copied}
              >
                {copied ? 'Copied!' : 'Copy Report'} <Download size={20} className="ml-2" />
              </button>
              <button onClick={handleGenerateToolLink} className="bg-orange-500 hover:bg-orange-700 text-white font-bold py-2 px-4 rounded mr-2">
                Generate Tool Link <Share size={20} className="ml-2" />
              </button>
              {toolLink && (
                <div className="mt-4">
                  <p>Tool Link:</p>
                  <a href={toolLink} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-900">
                    {toolLink}
                  </a>
                </div>
              )}
              <div className="mt-4">
                <h4>Saved Reports:</h4>
                <ul>
                  {savedReports.map((report) => (
                    <li key={report.id}>{report.title} ({report.timestamp})</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          <div className="mt-4">
            <button onClick={handlePreviousStep} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded">
              <ArrowLeft size={20} className="mr-2" /> Previous
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
