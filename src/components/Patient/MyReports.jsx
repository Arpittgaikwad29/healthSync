import React, { useState, useEffect } from 'react';

function MyReports({ userId }) {
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchReports = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`http://localhost:8000/api/patient/${userId}/summary`);
      const data = await response.json();
      
      if (response.ok) {
        setReports(data);
      } else {
        setError(data.detail || 'Failed to fetch reports');
      }
    } catch (err) {
      setError('Unable to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>My Medical Reports</h1>
          <p className="text-muted">View your complete medical history and analysis</p>
        </div>
        <button onClick={fetchReports} className="btn btn-primary" disabled={loading}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M1 4V10H7M23 20V14H17M20.49 9C19.9828 7.56678 19.1209 6.28536 17.9845 5.27543C16.8482 4.26551 15.4745 3.55976 13.9917 3.22426C12.5089 2.88875 10.9652 2.93434 9.50481 3.35677C8.04437 3.77921 6.71475 4.56471 5.64 5.64L1 10M23 14L18.36 18.36C17.2853 19.4353 15.9556 20.2208 14.4952 20.6432C13.0348 21.0657 11.4911 21.1112 10.0083 20.7757C8.52547 20.4402 7.1518 19.7345 6.01547 18.7246C4.87913 17.7146 4.01717 16.4332 3.51 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {loading ? 'Loading...' : 'Refresh Reports'}
        </button>
      </div>

      <div className="page-content">
        {error && (
          <div className="alert alert-error">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {error}
          </div>
        )}

        {!reports && !loading && !error && (
          <div className="empty-state">
            <div className="empty-icon">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none">
                <path d="M9 11L12 14L22 4M21 12V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h3>No Reports Yet</h3>
            <p>Click "Refresh Reports" to load your medical records or upload a new prescription to get started.</p>
          </div>
        )}

        {loading && (
          <div className="loading-container">
            <div className="pulse-loader"></div>
            <p>Loading your medical reports...</p>
          </div>
        )}

        {reports && !loading && (
          <div className="reports-grid">
            <div className="report-card summary-card">
              <div className="card-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M16 21V19C16 17.9391 15.5786 16.9217 14.8284 16.1716C14.0783 15.4214 13.0609 15 12 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21M12 11C14.2091 11 16 9.20914 16 7C16 4.79086 14.2091 3 12 3C9.79086 3 8 4.79086 8 7C8 9.20914 9.79086 11 12 11ZM20 8V14M23 11H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <h3>Medical Summary</h3>
                <div className="summary-content">
                  <pre>{reports.summary || 'No summary available'}</pre>
                </div>
              </div>
            </div>

            <div className="report-card">
              <div className="card-icon medications">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M4.5 16.5C3 15 3 12.5 4.5 11L11 4.5C12.5 3 15 3 16.5 4.5C18 6 18 8.5 16.5 10L10 16.5C8.5 18 6 18 4.5 16.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M13.5 7.5L16.5 10.5M8.5 2.5L10.5 4.5M2.5 8.5L4.5 10.5M7 13L11 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <h4>Current Medications</h4>
                <p className="card-description">Prescribed medicines and dosages</p>
                {reports.medications && reports.medications.length > 0 ? (
                  <ul className="medical-list">
                    {reports.medications.map((med, index) => (
                      <li key={index}>
                        <span className="badge badge-info">{med}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted">No medications recorded</p>
                )}
              </div>
            </div>

            <div className="report-card">
              <div className="card-icon diagnoses">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M22 12H18L15 21L9 3L6 12H2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <h4>Diagnoses</h4>
                <p className="card-description">Medical conditions and findings</p>
                {reports.diagnoses && reports.diagnoses.length > 0 ? (
                  <ul className="medical-list">
                    {reports.diagnoses.map((diag, index) => (
                      <li key={index}>
                        <span className="badge badge-warning">{diag}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted">No diagnoses recorded</p>
                )}
              </div>
            </div>

            <div className="report-card">
              <div className="card-icon recommendations">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <h4>Recommendations</h4>
                <p className="card-description">Doctor's advice and next steps</p>
                <div className="recommendations-content">
                  <pre>{reports.recommendations || 'No recommendations available'}</pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MyReports;
