# HABIBTI - Privacy-First Chat Application

A secure, end-to-end encrypted chat application with a unique hybrid social model.

## 🎯 Core Features

- **Chat without friendship**: Message anyone without friend requests
- **Social features require friendship**: Feeds and status visible only to accepted friends
- **Privacy-first**: Friends lists are private, no mutual friends visible
- **End-to-end encrypted**: Server acts as blind message relay
- **Ephemeral content**: 24-hour moments (feeds/status)

## 🏗️ Architecture

```
habibti/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # REST & WebSocket endpoints
│   │   ├── core/     # Config, security, encryption
│   │   ├── models/   # Database models
│   │   ├── services/ # Business logic
│   │   └── utils/    # Helpers
│   ├── tests/
│   └── requirements.txt
│
├── frontend/         # React web app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── utils/
│   │   └── App.jsx
│   └── package.json
│
└── docs/            # Documentation
    └── API.md
```

## 🚀 Tech Stack

### Backend
- **FastAPI** - Async Python web framework
- **MongoDB** - Document database
- **Redis** - Caching & real-time features
- **WebSockets** - Real-time communication
- **Cloudinary** - Media storage

### Frontend
- **React 18** - UI framework
- **TailwindCSS** - Styling
- **Web Crypto API** - Client-side encryption
- **IndexedDB** - Local storage

## 📦 Installation

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Configure environment variables
python -m app.main        # Run development server
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 🔧 Environment Variables

Create `backend/.env`:

```env
# Application
APP_NAME=habibti
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
MONGODB_URI=mongodb://localhost:27017/habibti
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-jwt-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=15

# OTP Service
OTP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=your-number

# Media Storage
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

## 📚 Documentation

- [Implementation Plan](../brain/79e66502-1ae0-4459-9037-f873f3d371be/implementation_plan.md)
- [Quick Reference](../brain/79e66502-1ae0-4459-9037-f873f3d371be/quick_reference.md)
- [API Documentation](docs/API.md)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 🚢 Deployment

### Free Tier Options
- **Backend**: Render / Railway
- **Database**: MongoDB Atlas (512MB free)
- **Cache**: Redis Cloud (30MB free)
- **Media**: Cloudinary (25GB free)

## 📝 Development Phases

- [x] **Phase 1**: MVP - Basic encrypted chat (Current)
- [ ] **Phase 2**: Social features - Friend requests
- [ ] **Phase 3**: Moments - 24h ephemeral content
- [ ] **Phase 4**: Advanced messaging - Media, voice
- [ ] **Phase 5**: Backup & multi-device
- [ ] **Phase 6**: Production hardening
- [ ] **Phase 7**: Android app

## 🔒 Security

- End-to-end encryption (ECDH + AES-256-GCM)
- OTP-based passwordless authentication
- Rate limiting on all endpoints
- HTTPS only in production
- No plaintext message storage

## 📄 License

MIT License - See LICENSE file for details

## 👥 Contributing

This is a personal project. Contributions welcome via pull requests.

---

**Built with privacy and security in mind** 🔐
