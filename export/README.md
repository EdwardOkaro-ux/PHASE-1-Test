# AfroFreight - Multi-Tenant Logistics SaaS Platform

## Export Package Contents

```
AfroFreight_Complete_Export_Feb14_2026/
├── README.md                    # This file
├── docs/
│   ├── 01_DATABASE_SCHEMA.md   # Complete database documentation
│   ├── 02_PROGRESS_REPORT.md   # Features completed/pending
│   ├── 03_RESUMPTION_GUIDE.md  # How to continue development
│   ├── 04_PRD.md               # Product Requirements Document
│   └── ENV_TEMPLATE.md         # Environment variables template
├── src/
│   ├── backend/
│   │   ├── server.py           # FastAPI application
│   │   ├── requirements.txt    # Python dependencies
│   │   ├── .env.example        # Environment template
│   │   └── tests/              # Test files
│   └── frontend/
│       ├── package.json        # NPM dependencies
│       ├── tailwind.config.js  # Tailwind CSS config
│       ├── public/             # Static assets
│       ├── src/                # React source code
│       └── .env.example        # Environment template
└── test_reports/
    └── iteration_*.json        # Test results
```

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- MongoDB 6.0+
- Yarn

### Backend Setup
```bash
cd src/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your MongoDB URL and Emergent credentials
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup
```bash
cd src/frontend
yarn install
cp .env.example .env
# Edit .env with backend URL
yarn start
```

## Project Status

- **Phase 1-5:** ✅ Complete
- **Phase 6+:** Pending

See `docs/02_PROGRESS_REPORT.md` for detailed status.

## Documentation

| Document | Description |
|----------|-------------|
| DATABASE_SCHEMA.md | All 16 tables with columns, types, and relationships |
| PROGRESS_REPORT.md | Features completed, pending, test results |
| RESUMPTION_GUIDE.md | Step-by-step guide to continue development |
| PRD.md | Product Requirements Document |

## Key Features Implemented

- Multi-tenant architecture with subdomain isolation
- Google OAuth authentication (via Emergent)
- Client management with custom rates
- Shipment tracking with barcode system
- Trip management with expenses
- Invoice and payment management
- Fleet management with compliance tracking
- Dark/light theme with persistence

## Tech Stack

- **Backend:** FastAPI, Python 3.11, Motor (async MongoDB)
- **Frontend:** React 18, Tailwind CSS, Shadcn/UI
- **Database:** MongoDB
- **Auth:** Emergent-managed Google OAuth

---

*Export generated: February 14, 2026*
