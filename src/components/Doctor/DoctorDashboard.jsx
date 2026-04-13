import React, { useState } from 'react';
import '../Patient/PatientDashboard.css';
import './DoctorDashboard.css';

function DoctorDashboard({ user, onLogout }) {
  const [patientId, setPatientId] = useState('');
  const [patientData, setPatientData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!patientId.trim()) {
      setError('Please enter a patient ID');
      return;
    }

    setLoading(true);
    setError('');
    setPatientData(null);

    try {
      const response = await fetch(`http://localhost:8000/api/patient/${patientId}/summary`);
      const data = await response.json();

      if (response.ok) {
        setPatientData(data);
      } else {
        setError(data.detail || 'Patient not found');
      }
    } catch (err) {
      setError('Unable to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-container doctor-dashboard">
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo-container">
            <div className="logo-icon-small">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 3H5C3.89543 3 3 3.89543 3 5V19C3 20.1046 3.89543 21 5 21H19C20.1046 21 21 20.1046 21 19V5C21 3.89543 20.1046 3 19 3Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M12 8V16M8 12H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            {sidebarOpen && <span className="brand-name-small">MediGraph</span>}
          </div>
        </div>

        <div className="sidebar-user">
          <div className="user-avatar doctor-avatar">
            {user.id.charAt(0).toUpperCase()}
          </div>
          {sidebarOpen && (
            <div className="user-info">
              <p className="user-name">Dr. {user.id}</p>
              <p className="user-role">Physician</p>
            </div>
          )}
        </div>

        <div className="doctor-stats">
          {sidebarOpen && (
            <>
              <div className="stat-item">
                <div className="stat-icon">👥</div>
                <div>
                  <p className="stat-label">Patients</p>
                  <p className="stat-value">Access All</p>
                </div>
              </div>
              <div className="stat-item">
                <div className="stat-icon">🔒</div>
                <div>
                  <p className="stat-label">Security</p>
                  <p className="stat-value">HIPAA Compliant</p>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="sidebar-footer">
          <button onClick={onLogout} className="logout-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9M16 17L21 12M21 12L16 7M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M3 12H21M3 6H21M3 18H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      <div className={`dashboard-main ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="page-container">
          <div className="page-header">
            <div>
              <h1>Patient Records</h1>
              <p className="text-muted">Access and review patient medical information</p>
            </div>
          </div>

          <div className="page-content">
            <div className="search-section">
              <div className="search-card">
                <div className="search-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                    <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
                    <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
                <h2>Search Patient Records</h2>
                <p>Enter patient's Aadhar number to retrieve medical information</p>
                
                <form onSubmit={handleSearch} className="search-form">
                  <div className="search-input-group">
                    <input
                      type="text"
                      className="form-input search-input"
                      placeholder="Enter Patient Aadhar Number"
                      value={patientId}
                      onChange={(e) => setPatientId(e.target.value)}
                      disabled={loading}
                    />
                    <button type="submit" className="btn btn-primary search-btn" disabled={loading}>
                      {loading ? (
                        <>
                          <span className="spinner"></span>
                          Searching...
                        </>
                      ) : (
                        <>
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                            <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
                            <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                          </svg>
                          Search
                        </>
                      )}
                    </button>
                  </div>
                </form>

                {error && (
                  <div className="alert alert-error mt-3">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    {error}
                  </div>
                )}
              </div>
            </div>

            {loading && (
              <div className="loading-container mt-4">
                <div className="pulse-loader"></div>
                <p>Retrieving patient records...</p>
              </div>
            )}

            {patientData && !loading && (
              <div className="patient-results">
                <div className="result-header">
                  <div className="patient-info-header">
                    <div className="patient-avatar-large">
                      {patientId.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h2>Patient: {patientId}</h2>
                      <p className="text-muted">Medical Records Retrieved</p>
                    </div>
                  </div>
                  <button 
                    className="btn btn-secondary"
                    onClick={() => {
                      setPatientData(null);
                      setPatientId('');
                    }}
                  >
                    New Search
                  </button>
                </div>

                <div className="reports-grid mt-4">
                  <div className="report-card summary-card">
                    <div className="card-icon">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                        <path d="M16 21V19C16 17.9391 15.5786 16.9217 14.8284 16.1716C14.0783 15.4214 13.0609 15 12 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21M12 11C14.2091 11 16 9.20914 16 7C16 4.79086 14.2091 3 12 3C9.79086 3 8 4.79086 8 7C8 9.20914 9.79086 11 12 11ZM20 8V14M23 11H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <div>
                      <h3>Medical Summary</h3>
                      <div className="summary-content">
                        <pre>{patientData.summary || 'No summary available'}</pre>
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
                      {patientData.medications && patientData.medications.length > 0 ? (
                        <ul className="medical-list">
                          {patientData.medications.map((med, index) => (
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
                      {patientData.diagnoses && patientData.diagnoses.length > 0 ? (
                        <ul className="medical-list">
                          {patientData.diagnoses.map((diag, index) => (
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
                      <h4>Treatment Plan</h4>
                      <p className="card-description">Recommendations and next steps</p>
                      <div className="recommendations-content">
                        <pre>{patientData.recommendations || 'No recommendations available'}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DoctorDashboard;
