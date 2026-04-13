import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import PatientDashboard from './components/Patient/PatientDashboard';
import DoctorDashboard from './components/Doctor/DoctorDashboard';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

useEffect(() => {
  // Check if user is logged in (from localStorage)
  const storedUser = localStorage.getItem('user');
  if (storedUser) {
    setUser(JSON.parse(storedUser));
  }
  
  // TEMPORARY: Auto-login for testing (REMOVE LATER)
  // setUser({ id: 'DOC456', type: 'Doctor' }); // Change to 'Doctor' to see doctor dashboard
  
  setLoading(false);
}, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="pulse-loader"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="app">
        <Routes>
          <Route 
            path="/" 
            element={
              user ? (
                <Navigate to={user.type === 'Patient' ? '/patient' : '/doctor'} />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
          <Route 
            path="/login" 
            element={
              user ? (
                <Navigate to={user.type === 'Patient' ? '/patient' : '/doctor'} />
              ) : (
                <Login onLogin={handleLogin} />
              )
            } 
          />
          <Route 
            path="/register" 
            element={
              user ? (
                <Navigate to={user.type === 'Patient' ? '/patient' : '/doctor'} />
              ) : (
                <Register />
              )
            } 
          />
          <Route 
            path="/patient/*" 
            element={
              user && user.type === 'Patient' ? (
                <PatientDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
          <Route 
            path="/doctor/*" 
            element={
              user && user.type === 'Doctor' ? (
                <DoctorDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
