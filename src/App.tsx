import React, { useState, useEffect } from 'react';
import { ArrowLeft, Play, Pause } from 'lucide-react';

function App() {
  const [counter, setCounter] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoIncrementInterval, setAutoIncrementInterval] = useState<number | null>(null);
  const [storedCounter, setStoredCounter] = useState(() => {
    const stored = localStorage.getItem('counter');
    return stored ? parseInt(stored, 10) : 0;
  });

  useEffect(() => {
    document.title = `Counter: ${counter}`;
    localStorage.setItem('counter', counter.toString());
  }, [counter]);

  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => setCounter(prev => prev + 1), 1000);
      setAutoIncrementInterval(interval);
    } else {
      autoIncrementInterval && clearInterval(autoIncrementInterval);
      setAutoIncrementInterval(null);
    }
    return () => autoIncrementInterval && clearInterval(autoIncrementInterval);
  }, [isPlaying]);

  const handleIncrement = () => setCounter(counter + 1);
  const handleDecrement = () => setCounter(counter - 1);
  const handleTogglePlay = () => setIsPlaying(prev => !prev);
  const handleReset = () => {
    setCounter(0);
    setIsPlaying(false);
    localStorage.removeItem('counter');
  };

  useEffect(() => {
    setCounter(storedCounter);
  }, [storedCounter]);

  return (
    <div className="flex flex-col justify-center items-center h-screen bg-gray-100">
      <header className="text-3xl font-bold mb-4">
        <p>AI Start Up Database Project</p>
        <p>Current Step: Problem Solving (Patch)</p>
      </header>
      <div className="flex gap-4 mb-4">
        <button onClick={handleDecrement} className="px-4 py-2 bg-red-500 text-white rounded">
          <ArrowLeft size={24} /> Decrement
        </button>
        <div className="text-2xl font-bold">Counter: {counter}</div>
        <button onClick={handleIncrement} className="px-4 py-2 bg-green-500 text-white rounded">
          Increment <ArrowLeft size={24} transform="rotate(180deg)" />
        </button>
      </div>
      <button onClick={handleTogglePlay} className={`px-4 py-2 rounded ${isPlaying ? 'bg-orange-500' : 'bg-blue-500'} text-white`}> 
        {isPlaying ? <Pause size={24} /> : <Play size={24} />} {isPlaying ? 'Pause' : 'Play'}
      </button>
      <button onClick={handleReset} className="px-4 py-2 bg-purple-500 text-white rounded mt-4">
        Reset & Save Point
      </button>
    </div>
  );
}

export default App;