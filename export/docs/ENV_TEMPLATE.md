# AfroFreight Environment Variables Template

# ===========================================
# BACKEND CONFIGURATION
# ===========================================
# File: /app/backend/.env

# MongoDB Connection
MONGO_URL=mongodb://localhost:27017
DB_NAME=logistics_db

# Emergent Authentication (Google OAuth)
# Get these from your Emergent dashboard
EMERGENT_CLIENT_ID=your_emergent_client_id_here
EMERGENT_CLIENT_SECRET=your_emergent_client_secret_here

# ===========================================
# FRONTEND CONFIGURATION
# ===========================================
# File: /app/frontend/.env

# Backend API URL
# For local development:
REACT_APP_BACKEND_URL=http://localhost:8001

# For production:
# REACT_APP_BACKEND_URL=https://your-domain.com

# ===========================================
# OPTIONAL: Future Integrations
# ===========================================

# Twilio (WhatsApp Notifications)
# TWILIO_ACCOUNT_SID=your_account_sid
# TWILIO_AUTH_TOKEN=your_auth_token
# TWILIO_WHATSAPP_NUMBER=+14155238886

# SendGrid (Email Notifications)
# SENDGRID_API_KEY=your_sendgrid_api_key
# SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# Stripe (Payment Processing)
# STRIPE_SECRET_KEY=sk_test_xxx
# STRIPE_WEBHOOK_SECRET=whsec_xxx
