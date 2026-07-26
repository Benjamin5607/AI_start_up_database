import React, { useState, useEffect } from 'react';
import { ArrowLeft, Play, CheckCircle, XCircle, Info } from 'lucide-react';

function App() {
  const [currentStep, setCurrentStep] = useState(1); // 1: Persona, 2: Prompt Generation, 3: Checklist, 4: Tool Integration, 5: Review
  const [persona, setPersona] = useState('');
  const [prompt, setPrompt] = useState('');
  const [checklist, setChecklist] = useState([]);
  const [tools, setTools] = useState([]);
  const [resumeStep, setResumeStep] = useState(1);
  const [reportGenerated, setReportGenerated] = useState(false);

  const steps = [
    { id: 1, name: 'Define Persona', description: 'Create Project Persona' },
    { id: 2, name: 'Generate Prompt', description: 'Craft AI Prompt' },
    { id: 3, name: 'Setup Checklist', description: 'Configure Project Checklist' },
    { id: 4, name: 'Integrate Tools', description: 'Connect Relevant Tools' },
    { id: 5, name: 'Review & Finalize', description: 'Final Review and Report Generation' }
  ];

  const handlePersonaSubmit = (e) => {
    e.preventDefault();
    setPersona(e.target.persona.value);
    setCurrentStep(2);
  };

  const handlePromptGenerate = () => {
    const generatedPrompt = `Based on persona: ${persona}, generate content...`;
    setPrompt(generatedPrompt);
    setCurrentStep(3);
  };

  const handleChecklistAdd = (item) => {
    setChecklist([...checklist, item]);
  };

  const handleToolAdd = (tool) => {
    setTools([...tools, tool]);
  };

  const handleGenerateReport = () => {
    setReportGenerated(true);
    setTimeout(() => {
      setCurrentStep(5);
    }, 1000);
  };

  const handleContinue = () => {
    if (currentStep < steps.length) {
      setCurrentStep((prevStep) => prevStep + 1);
    }
  };

  const handleResume = () => {
    setCurrentStep(resumeStep);
  };

  const handleStepBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prevStep) => prevStep - 1);
    }
  };

  useEffect(() => {
    // Simulate resuming from storage
    const storedStep = localStorage.getItem('lastStep');
    if (storedStep) {
      setResumeStep(parseInt(storedStep));
    }
    // Update last step in storage on step change
    localStorage.setItem('lastStep', currentStep);
  }, [currentStep]);

  return (
    <div className="flex flex-col justify-center items-center h-screen bg-gray-100">
      <header className="text-3xl font-bold mb-4">
        <p>AI Start Up Database Project Workflow</p>
        <p className="text-xl">Current Step: {steps.find(s => s.id === currentStep)?.name} ({currentStep}/{steps.length})</p>
        {reportGenerated && <p className="text-green-500">Report Generated Successfully!</p>}
      </header>
      {currentStep === 1 && (
        <form onSubmit={handlePersonaSubmit} className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2" htmlFor="persona">
            Persona Description:
          </label>
          <textarea
            id="persona"
            name="persona"
            rows="4"
            className="block w-full p-2.5 bg-gray-50 border border-gray-300 text-sm text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            required
          />
          <button type="submit" className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Submit Persona <Play size={20} />
          </button>
        </form>
      )}
      {currentStep === 2 && (
        <div className="mb-4">
          <p>Generated Prompt: {prompt || 'None'}</p>
          <button onClick={handlePromptGenerate} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Generate Prompt <Play size={20} />
          </button>
          <button onClick={handleContinue} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded ml-2">
            Continue <Play size={20} />
          </button>
        </div>
      )}
      {currentStep === 3 && (
        <div className="mb-4">
          <h2 className="text-xl mb-2">Checklist:</h2>
          <ul>
            {checklist.map((item, index) => (
              <li key={index} className="flex items-center mb-2">
                <CheckCircle size={20} className="text-green-500 mr-2" />
                {item}
                <XCircle
                  size={18}
                  className="text-red-500 cursor-pointer ml-4"
                  onClick={() => setChecklist(checklist.filter((i, idx) => idx !== index))}
                />
              </li>
            ))}
          </ul>
          <input
            type="text"
            className="block w-full p-2.5 bg-gray-50 border border-gray-300 text-sm text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 mb-2"
            placeholder="Add new checklist item"
            onKeyPress={(e) => e.key === 'Enter' && handleChecklistAdd(e.target.value) && e.target.value && (e.target.value = '')}
          />
          <button onClick={handleContinue} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Continue <Play size={20} />
          </button>
        </div>
      )}
      {currentStep === 4 && (
        <div className="mb-4">
          <h2 className="text-xl mb-2">Integrated Tools:</h2>
          <ul>
            {tools.map((tool, index) => (
              <li key={index} className="flex items-center mb-2">
                <CheckCircle size={20} className="text-green-500 mr-2" />
                {tool}
                <XCircle
                  size={18}
                  className="text-red-500 cursor-pointer ml-4"
                  onClick={() => setTools(tools.filter((t, idx) => idx !== index))}
                />
              </li>
            ))}
          </ul>
          <input
            type="text"
            className="block w-full p-2.5 bg-gray-50 border border-gray-300 text-sm text-gray-900 rounded-lg focus:ring-blue-500 focus:border-blue-500 mb-2"
            placeholder="Add new tool"
            onKeyPress={(e) => e.key === 'Enter' && handleToolAdd(e.target.value) && e.target.value && (e.target.value = '')}
          />
          <button onClick={handleGenerateReport} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Generate Report <Info size={20} />
          </button>
          <button onClick={handleStepBack} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded ml-2">
            Back <ArrowLeft size={20} />
          </button>
        </div>
      )}
      {currentStep === 5 && (
        <div>
          <p className="text-2xl">Review Your Workflow:</p>
          <ul className="list-disc pl-4 mb-4">
            <li>Persona: {persona}</li>
            <li>Prompt: {prompt}</li>
            <li>Checklist: {checklist.join(', ')}</li>
            <li>Tools: {tools.join(', ')}</li>
          </ul>
          <button onClick={handleResume} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded">
            Resume from Last Step <ArrowLeft size={20} />
          </button>
        </div>
      )}
      <div className="absolute bottom-0 left-0 p-4">
        <button onClick={handleStepBack} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded">
          Back <ArrowLeft size={20} />
        </button>
        {currentStep !== 1 && (
          <button onClick={handleResume} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded ml-2">
            Resume from Last Step <ArrowLeft size={20} />
          </button>
        )}
      </div>
    </div>
  );
}

export default App;