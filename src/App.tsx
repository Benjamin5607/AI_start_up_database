import React, { useState, useEffect } from 'react';
import { ArrowLeft, Play } from 'lucide-react';

function App() {
  const [currentStep, setCurrentStep] = useState(1); // 1: Deployment, 2: Configuration, 3: Launch
  const [isPlaying, setIsPlaying] = useState(false);
  const steps = [
    { id: 1, name: 'Deployment (Deploy)', description: 'Deploying application...' },
    { id: 2, name: 'Configuration', description: 'Configuring settings...' },
    { id: 3, name: 'Launch', description: 'Launching the application...' }
  ];

  useEffect(() => {
    if (isPlaying) {
      const intervalId = setInterval(() => {
        if (currentStep < steps.length) {
          setCurrentStep(prevStep => prevStep + 1);
        } else {
          setIsPlaying(false);
        }
      }, 2000); // Auto-proceed every 2 seconds
      return () => clearInterval(intervalId);
    }
  }, [isPlaying, currentStep, steps.length]);

  const handleButtonClick = () => {
    if (isPlaying) {
      setIsPlaying(false);
    } else {
      setIsPlaying(true);
    }
  };

  const handleStepBack = () => {
    if (currentStep > 1) {
      setCurrentStep(prevStep => prevStep - 1);
      setIsPlaying(false);
    }
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-100">
      <header className="bg-orange-500 p-4 rounded">
        <p className="text-2xl text-white">AI Start Up Database Project</p>
        <div className="mt-4">
          <p className="text-lg text-white">Current Step: {steps[currentStep - 1].name}</p>
          <p className="text-sm text-white">{steps[currentStep - 1].description}</p>
        </div>
        <div className="flex justify-center mt-4">
          <button onClick={handleStepBack} className="bg-gray-300 hover:bg-gray-400 text-black font-bold py-2 px-4 rounded mr-2" disabled={currentStep === 1}">
            <ArrowLeft size={20} /> Back
          </button>
          <button onClick={handleButtonClick} className={`bg-${isPlaying ? 'red' : 'blue'}-500 hover:bg-${isPlaying ? 'red' : 'blue'}-700 text-white font-bold py-2 px-4 rounded`}">
            {isPlaying ? 'Stop' : 'Start'} {isPlaying && <Play size={20} />} 
          </button>
        </div>
        <div className="mt-4 text-sm text-white">
          {currentStep === steps.length ? 'Process Completed!' : `Step ${currentStep} of ${steps.length}`}
        </div>
      </header>
      <div className="absolute bottom-0 left-0 p-4 text-gray-500">
        <small>Auto-proceeds every 2 seconds when playing.</small>
      </div>
    </div>
  );
}

export default App;