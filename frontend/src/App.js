import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Landing } from './pages/Landing';
import { Dashboard } from './pages/Dashboard';
import { Clients } from './pages/Clients';
import { Shipments } from './pages/Shipments';
import { LoadingStaging } from './pages/LoadingStaging';
import { Trips } from './pages/Trips';
import { TripDetail } from './pages/TripDetail';
import { Scanner } from './pages/Scanner';
import { Finance } from './pages/Finance';
import { Fleet } from './pages/Fleet';
import { ParcelIntake } from './pages/ParcelIntake';
import { Warehouse } from './pages/Warehouse';
import { Team } from './pages/Team';
import { Settings } from './pages/Settings';
import { Toaster } from './components/ui/sonner';
import './App.css';

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clients"
        element={
          <ProtectedRoute>
            <Clients />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clients/new"
        element={
          <ProtectedRoute>
            <Clients />
          </ProtectedRoute>
        }
      />
      <Route
        path="/loading"
        element={
          <ProtectedRoute>
            <LoadingStaging />
          </ProtectedRoute>
        }
      />
      <Route
        path="/shipments"
        element={
          <ProtectedRoute>
            <Shipments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/shipments/new"
        element={
          <ProtectedRoute>
            <Shipments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/parcels/intake"
        element={
          <ProtectedRoute>
            <ParcelIntake />
          </ProtectedRoute>
        }
      />
      <Route
        path="/warehouse"
        element={
          <ProtectedRoute>
            <Warehouse />
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips"
        element={
          <ProtectedRoute>
            <Trips />
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips/:tripId"
        element={
          <ProtectedRoute>
            <TripDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips/new"
        element={
          <ProtectedRoute>
            <Trips />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scanner"
        element={
          <ProtectedRoute>
            <Scanner />
          </ProtectedRoute>
        }
      />
      <Route
        path="/finance"
        element={
          <ProtectedRoute>
            <Finance />
          </ProtectedRoute>
        }
      />
      <Route
        path="/fleet"
        element={
          <ProtectedRoute>
            <Fleet />
          </ProtectedRoute>
        }
      />
      <Route
        path="/team"
        element={
          <ProtectedRoute>
            <Team />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
