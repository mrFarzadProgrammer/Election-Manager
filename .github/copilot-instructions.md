# Copilot Instructions for Election Manager

## Project Overview
Election Manager is a full-stack election/voting system with:
- **Backend**: FastAPI + SQLAlchemy with SQLite/PostgreSQL
- **Frontend**: React 19 + TypeScript with Vite + Recharts for visualizations
- **Key Domain**: Candidate registration, voter management, plans/packages, ticket system
- **Language**: Content supports Persian (Farsi) labels and RTL UI components

## Architecture & Key Patterns

### Backend Structure (FastAPI)
- **main.py**: Core FastAPI app with all endpoints, CORS configured for localhost:5173, :3000, :5555
- **models.py**: SQLAlchemy ORM models - `User`, `Candidate`, `Plan`, `Ticket` with relationships
- **database.py**: Session management with `SessionLocal`, `get_db()` dependency
- **auth.py**: JWT token handling (access + refresh tokens), password hashing with bcrypt
- **schemas.py**: Pydantic request/response models for validation

**Critical Auth Pattern**: 
- Tokens extracted from `Authorization: Bearer <token>` header using `get_current_user()` dependency
- Two-tier roles: `ADMIN` (registrations, candidate management) and `CANDIDATE` (self-service updates)
- `get_admin_user()` and similar decorators enforce role-based access

### Database Schema
- **User**: username/email/phone unique constraints - stores credentials
- **Candidate**: Linked to User (user_id foreign key), stores bot_token/bot_name for Telegram integration, includes Persian date field `created_at_jalali` 
- **Plan**: Pricing tiers per candidate with JSON `features` field and color customization
- **Ticket**: User support tickets linked to candidates

### Frontend Components
- **App.tsx**: Main container managing auth state, data fetching, login/logout, delegates to `AdminPanel` or `CandidatePanel`
- **AdminPanel**: Admin-only views for candidate/plan management
- **CandidatePanel**: Self-service candidate profile/bot config updates
- **api.ts**: Centralized API client with error message extraction; all endpoints prefixed with `/api/`

## Developer Workflows

### Running the Application
**Backend**: `cd backend && pip install -r requirements.txt && python -m uvicorn main:app --reload` (runs on :8000)
**Frontend**: `cd frontend && npm install && npm run dev` (Vite dev server on :5173)

### Database Operations
- **Reset DB**: `python backend/reset_db.py` - drops/recreates all tables
- **Seed Data**: `python backend/seed_data.py` - populates test candidates/plans
- **Verification**: Prefer running Uvicorn + exercising critical flows, and running `npm run build` for frontend

### Key Testing Files
- Database tests verify integrity constraints (duplicate username/email/phone/bot_token)

## Project-Specific Conventions

### Error Handling
- **IntegrityError parsing**: Extract field names from SQLite "UNIQUE constraint failed" messages
- **Persian error messages**: Use `FIELD_LABELS` dict in main.py to map field names to Persian labels for user display
- **API error response format**: `{ "code": "DUPLICATE_FIELD", "field": "username", "label": "نام کاربری", "message": "..." }`

### Field Validation & Uniqueness
- Username, email, phone, bot_token, bot_name must be unique per candidate/user
- Phone/bot fields strip whitespace before storage: `field.strip() or None`
- City/province are optional; default to None if empty
- Bot configuration stored as JSON in `CandidateUpdate.bot_config`

### Telegram Integration
- Candidates store `bot_token` (Telegram bot API key) and `bot_name` in their profile
- Backend validates these during create/update but doesn't enforce API calls (client handles bot interaction)
- Backend serves as registry; actual bot operations delegated to frontend or separate bot service

### Persian Date Handling
- Import: `import jdatetime`
- Created timestamp stored both as UTC (`created_at`) and Persian (`created_at_jalali`) 
- Format Persian dates: `jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")`

### Frontend Data Fetching Pattern
- Load data in `useEffect()` on component mount
- Store in local state (candidates, plans, tickets) rather than global state management
- Graceful error handling with Persian error messages to user
- Type-safe: Use interfaces from `types.ts` (User, Candidate, Plan, Ticket)

## Integration Points & Dependencies

### External Libraries
**Backend**: fastapi, sqlalchemy, pydantic, python-jose (JWT), passlib (password hashing), python-telegram-bot, httpx
**Frontend**: react-router-dom (routing), recharts (charts), lucide-react (icons)

### API Contract
- All endpoints return JSON; authentication via Bearer tokens in Authorization header
- Pagination: Not implemented; endpoints return full lists
- Base URL: `/api` prefix; register, login, candidates, plans, tickets, admin endpoints

### CORS Configuration
Currently allows: `localhost:5173` (Vite default), `localhost:3000` (alternate frontend), `localhost:5555` (testing)
Update in `main.py` CORSMiddleware if deploying to production origin

## Common Tasks & Patterns

### Adding a New Endpoint
1. Define Pydantic schema in `schemas.py`
2. Add route in `main.py` with appropriate `Depends(database.get_db)` and role checks
3. Wrap IntegrityError with `raise_from_integrity_error(e)` for duplicate field handling
4. Update `api.ts` with fetch wrapper and types

### Debugging Database State
- Use `python backend/reset_db.py` to start fresh
- Check `election_manager.db` file location (repo root by default)
- Inspect `seed_data.py` for example structure

### Auth Flow
User → POST `/api/auth/login` → returns access_token + refresh_token → stored in localStorage → passed as `Authorization: Bearer {token}` on subsequent requests → decoded in `get_current_user()`

## Files to Reference for Patterns
- **[backend/main.py](backend/main.py#L40-L100)**: Error handling & duplicate field logic
- **[backend/auth.py](backend/auth.py#L60-L90)**: Token extraction from headers  
- **[backend/models.py](backend/models.py#L30-L50)**: ORM relationships (User ↔ Candidate ↔ Plan)
- **[frontend/src/services/api.ts](frontend/src/services/api.ts#L1-L50)**: Error message extraction pattern
- **[frontend/src/App.tsx](frontend/src/App.tsx#L50-L90)**: useEffect data loading pattern
