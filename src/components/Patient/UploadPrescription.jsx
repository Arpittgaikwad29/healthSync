import React, { useState } from 'react';

function UploadPrescription({ userId }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(0);
  const [agentResults, setAgentResults] = useState({});
  const [finalResult, setFinalResult] = useState(null);
  const [error, setError] = useState('');

  const agents = [
    { id: 1, name: 'OCR Extraction', icon: '🔍', description: 'Extracting text from image' },
    { id: 2, name: 'Text Correction', icon: '✏️', description: 'Correcting spelling errors' },
    { id: 3, name: 'Understanding', icon: '🧠', description: 'Extracting medical information' },
    { id: 4, name: 'FHIR Conversion', icon: '📋', description: 'Converting to standard format' },
    { id: 5, name: 'Graph Database', icon: '🗄️', description: 'Storing in knowledge graph' },
    { id: 6, name: 'Analysis', icon: '📊', description: 'Generating medical insights' }
  ];

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError('');
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setProcessing(true);
    setCurrentAgent(0);
    setAgentResults({});
    setFinalResult(null);
    setError('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('patient_id', userId);

    try {
      const response = await fetch('http://localhost:8000/api/process-prescription', {
        method: 'POST',
        body: formData
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.agent) {
              setCurrentAgent(data.agent);
              if (data.result) {
                setAgentResults(prev => ({
                  ...prev,
                  [data.agent]: data.result
                }));
              }
            }
            
            if (data.final) {
              setFinalResult(data.final);
            }

            if (data.error) {
              setError(data.error);
            }
          }
        }
      }
    } catch (err) {
      setError('Failed to process prescription. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setPreview(null);
    setProcessing(false);
    setCurrentAgent(0);
    setAgentResults({});
    setFinalResult(null);
    setError('');
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Upload Prescription</h1>
          <p className="text-muted">Upload medical documents for AI-powered analysis</p>
        </div>
      </div>

      <div className="page-content">
        {!processing && !finalResult && (
          <div className="upload-section">
            <div className="upload-area">
              {!preview ? (
                <label className="upload-dropzone">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                  />
                  <div className="dropzone-content">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                      <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15M17 8L12 3M12 3L7 8M12 3V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <h3>Drop your prescription here</h3>
                    <p>or click to browse</p>
                    <span className="file-types">Supports: JPG, PNG, BMP</span>
                  </div>
                </label>
              ) : (
                <div className="preview-container">
                  <img src={preview} alt="Prescription preview" className="preview-image" />
                  <div className="preview-actions">
                    <button onClick={resetUpload} className="btn btn-secondary">
                      Change File
                    </button>
                    <button onClick={handleUpload} className="btn btn-primary">
                      Process Document
                    </button>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="alert alert-error mt-3">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {error}
              </div>
            )}
          </div>
        )}

        {processing && (
          <div className="processing-section">
            <h2 className="text-center mb-4">Processing Your Prescription</h2>
            
            <div className="agents-timeline">
              {agents.map((agent, index) => (
                <div 
                  key={agent.id} 
                  className={`agent-step ${
                    currentAgent > agent.id ? 'completed' : 
                    currentAgent === agent.id ? 'active' : 
                    'pending'
                  }`}
                >
                  <div className="agent-icon">{agent.icon}</div>
                  <div className="agent-info">
                    <h4>{agent.name}</h4>
                    <p>{agent.description}</p>
                    {agentResults[agent.id] && (
                      <div className="agent-result">
                        <pre>{JSON.stringify(agentResults[agent.id], null, 2)}</pre>
                      </div>
                    )}
                  </div>
                  {currentAgent === agent.id && (
                    <div className="agent-spinner">
                      <div className="pulse-loader-small"></div>
                    </div>
                  )}
                  {currentAgent > agent.id && (
                    <div className="agent-check">✓</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {finalResult && !processing && (
          <div className="result-section">
            <div className="success-header">
              <div className="success-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                  <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h2>Processing Complete!</h2>
              <p>Your prescription has been successfully analyzed and stored.</p>
            </div>

            <div className="result-card">
              <h3>Medical Analysis</h3>
              <div className="analysis-content">
                <pre>{finalResult}</pre>
              </div>
            </div>

            <div className="result-actions">
              <button onClick={resetUpload} className="btn btn-primary">
                Upload Another Prescription
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default UploadPrescription;
