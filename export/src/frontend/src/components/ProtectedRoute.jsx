import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export function ProtectedRoute({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading, isAuthenticated, checkAuth, setUser, setIsAuthenticated } = useAuth();

  useEffect(() => {
    // If user data passed from AuthCallback, use it directly
    if (location.state?.user) {
      setUser(location.state.user);
      setIsAuthenticated(true);
      // Clear the state to prevent re-using
      window.history.replaceState({}, document.title);
      return;
    }

    // Otherwise, verify with server
    if (!loading && !isAuthenticated) {
      checkAuth().then(() => {
        // checkAuth will update state
      }).catch(() => {
        navigate('/', { replace: true });
      });
    }
  }, [location.state, loading, isAuthenticated, navigate, checkAuth, setUser, setIsAuthenticated]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated && !location.state?.user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return children;
}
