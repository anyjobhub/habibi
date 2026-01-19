# Backend Development Guide

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Local Services

You need MongoDB and Redis running locally or use cloud services:

**Option A: Local (Docker)**
```bash
# MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Redis
docker run -d -p 6379:6379 --name redis redis:latest
```

**Option B: Cloud (Free Tiers)**
- MongoDB Atlas: https://www.mongodb.com/cloud/atlas/register
- Redis Cloud: https://redis.com/try-free/

Update `.env` with connection strings.

### 4. Initialize Database

```bash
python -m app.utils.init_db
```

### 5. Run Development Server

```bash
python -m app.main
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── auth.py         # Authentication endpoints
│   │       └── __init__.py         # API router
│   ├── core/
│   │   ├── config.py               # Settings
│   │   ├── database.py             # MongoDB connection
│   │   ├── redis.py                # Redis connection
│   │   └── security.py             # JWT, OTP, hashing
│   ├── models/
│   │   ├── user.py                 # User models
│   │   └── otp.py                  # OTP session models
│   ├── services/
│   │   └── otp_service.py          # OTP SMS service
│   ├── utils/
│   │   └── init_db.py              # Database initialization
│   └── main.py                     # FastAPI application
├── tests/
├── .env                            # Environment variables (gitignored)
├── .env.example                    # Environment template
└── requirements.txt                # Python dependencies
```

## API Endpoints

### Authentication

#### POST /api/v1/auth/signup
Initiate signup by sending OTP to phone number.

**Request:**
```json
{
  "phone": "+919876543210",
  "purpose": "signup"
}
```

**Response:**
```json
{
  "session_id": "507f1f77bcf86cd799439011",
  "expires_in": 300
}
```

#### POST /api/v1/auth/verify-otp
Verify OTP code.

**Request:**
```json
{
  "session_id": "507f1f77bcf86cd799439011",
  "otp": "123456"
}
```

**Response:**
```json
{
  "verified": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### POST /api/v1/auth/complete-signup
Complete signup with user details.

**Request:**
```json
{
  "phone": "+919876543210",
  "username": "salman_dev",
  "name": "Salman",
  "public_key": "base64_encoded_public_key",
  "device_info": {
    "device_id": "uuid",
    "device_name": "Chrome on Linux",
    "public_key": "base64_encoded_device_key"
  }
}
```

**Query Parameter:** `temp_token` (from verify-otp response)

**Response:**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "phone": "+919876543210",
  "username": "salman_dev",
  "profile": {
    "name": "Salman",
    "bio": null,
    "avatar_url": null
  },
  "privacy": {
    "discoverable_by_phone": true,
    "discoverable_by_username": true,
    "show_online_status": true,
    "read_receipts": true
  },
  "devices": [...],
  "status": {
    "online": false,
    "last_seen": "2026-01-19T01:00:00Z"
  }
}
```

## Development Mode

In development mode (when Twilio is not configured), OTP codes are printed to console instead of being sent via SMS:

```
==================================================
OTP for +919876543210: 123456
==================================================
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

## Common Issues

### 1. MongoDB Connection Error
- Ensure MongoDB is running
- Check `MONGODB_URI` in `.env`
- For MongoDB Atlas, whitelist your IP

### 2. Redis Connection Error
- Ensure Redis is running
- Check `REDIS_URL` in `.env`

### 3. OTP Not Sending
- In development, OTPs are logged to console
- For production, configure Twilio credentials in `.env`

### 4. Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

## Next Steps

1. ✅ Authentication endpoints (complete)
2. ⏳ User management endpoints
3. ⏳ WebSocket server for real-time messaging
4. ⏳ Message encryption/decryption
5. ⏳ Friend request system
6. ⏳ Moments (feeds/status)

## Useful Commands

```bash
# Format code
black app/

# Lint code
flake8 app/

# Check types
mypy app/

# Run development server with auto-reload
uvicorn app.main:app --reload

# Run in production mode
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```
