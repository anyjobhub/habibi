# HABIBTI API Documentation

## Base URL
```
Development: http://localhost:8000/api/v1
Production: https://api.habibti.app/api/v1
```

## Authentication

All endpoints except `/auth/*` require authentication via JWT token in the `Authorization` header:

```
Authorization: Bearer <session_token>
```

---

## 📧 Authentication Endpoints

### POST /auth/signup
Initiate signup by sending OTP to email.

**Request:**
```json
{
  "email": "user@example.com",
  "purpose": "signup"
}
```

**Response:** `200 OK`
```json
{
  "session_id": "507f1f77bcf86cd799439011",
  "expires_in": 300,
  "message": "OTP sent successfully to user@example.com"
}
```

---

### POST /auth/verify-otp
Verify OTP code.

**Request:**
```json
{
  "session_id": "507f1f77bcf86cd799439011",
  "otp": "123456"
}
```

**Response:** `200 OK`
```json
{
  "verified": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "OTP verified successfully. Please complete your profile to continue."
}
```

---

### POST /auth/complete-signup
Complete signup with full profile.

**Query Parameters:**
- `temp_token` (required): Temporary token from OTP verification

**Request:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "mobile": "+919876543210",
  "address": "123 Main St, City, State 12345",
  "date_of_birth": "1995-01-15",
  "gender": "male",
  "bio": "Hello, I'm John!",
  "public_key": "base64_encoded_public_key",
  "device_info": {
    "device_id": "device-uuid",
    "device_name": "Chrome on Linux",
    "public_key": "base64_device_key"
  }
}
```

**Response:** `201 Created`
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "johndoe",
  "profile": {
    "full_name": "John Doe",
    "mobile": "+919876543210",
    "address": "123 Main St, City, State 12345",
    "date_of_birth": "1995-01-15",
    "gender": "male",
    "bio": "Hello, I'm John!",
    "avatar_url": null,
    "created_at": "2026-01-19T02:00:00Z"
  },
  "privacy": {
    "discoverable_by_email": true,
    "discoverable_by_username": true,
    "show_online_status": true,
    "read_receipts": true
  },
  "devices": [...],
  "status": {
    "online": false,
    "last_seen": "2026-01-19T02:00:00Z"
  }
}
```

---

### POST /auth/resend-otp
Resend OTP to email.

**Request:**
```json
{
  "email": "user@example.com",
  "purpose": "signup"
}
```

**Response:** `200 OK`
```json
{
  "session_id": "507f1f77bcf86cd799439012",
  "expires_in": 300,
  "message": "OTP resent successfully to user@example.com"
}
```

---

### GET /auth/me
Get current user profile.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response:** `200 OK`
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "johndoe",
  "profile": {...},
  "privacy": {...},
  "devices": [...],
  "status": {...}
}
```

---

## 💬 Conversation Endpoints

### POST /conversations
Create or get a conversation with another user.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Request:**
```json
{
  "participant_id": "507f1f77bcf86cd799439012"
}
```

**Response:** `201 Created`
```json
{
  "id": "507f1f77bcf86cd799439013",
  "type": "one_to_one",
  "participants": [
    {
      "user_id": "507f1f77bcf86cd799439012",
      "username": "janedoe",
      "full_name": "Jane Doe",
      "avatar_url": "https://...",
      "online": true,
      "last_seen": "2026-01-19T02:00:00Z"
    }
  ],
  "last_message": null,
  "unread_count": 0,
  "created_at": "2026-01-19T02:00:00Z",
  "updated_at": "2026-01-19T02:00:00Z"
}
```

---

### GET /conversations
Get all conversations for current user.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of conversations to return
- `skip` (optional, default: 0): Number of conversations to skip

**Response:** `200 OK`
```json
{
  "conversations": [
    {
      "id": "507f1f77bcf86cd799439013",
      "type": "one_to_one",
      "participants": [...],
      "last_message": {
        "message_id": "507f1f77bcf86cd799439014",
        "encrypted_preview": "...",
        "timestamp": "2026-01-19T02:00:00Z",
        "sender_id": "507f1f77bcf86cd799439012"
      },
      "unread_count": 3,
      "created_at": "2026-01-19T02:00:00Z",
      "updated_at": "2026-01-19T02:05:00Z"
    }
  ],
  "total": 10
}
```

---

### GET /conversations/{conversation_id}
Get a specific conversation.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response:** `200 OK`
```json
{
  "id": "507f1f77bcf86cd799439013",
  "type": "one_to_one",
  "participants": [...],
  "last_message": {...},
  "unread_count": 0,
  "created_at": "2026-01-19T02:00:00Z",
  "updated_at": "2026-01-19T02:00:00Z"
}
```

---

### DELETE /conversations/{conversation_id}
Archive a conversation (delete for current user).

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response:** `204 No Content`

---

## 📨 Message Endpoints

### POST /messages
Send a new message.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Request:**
```json
{
  "conversation_id": "507f1f77bcf86cd799439013",
  "encrypted_content": "base64_encrypted_message_blob",
  "content_type": "text",
  "recipient_keys": [
    {
      "user_id": "507f1f77bcf86cd799439012",
      "device_id": "device-uuid",
      "encrypted_key": "base64_encrypted_symmetric_key"
    }
  ],
  "reply_to": null,
  "is_ephemeral": false,
  "ttl_seconds": null,
  "view_once": false
}
```

**Response:** `201 Created`
```json
{
  "id": "507f1f77bcf86cd799439014",
  "conversation_id": "507f1f77bcf86cd799439013",
  "sender_id": "507f1f77bcf86cd799439011",
  "encrypted_content": "base64_encrypted_message_blob",
  "content_type": "text",
  "recipient_keys": [...],
  "metadata": {
    "media_url": null,
    "reply_to": null,
    "is_ephemeral": false
  },
  "status": {
    "sent_at": "2026-01-19T02:00:00Z",
    "delivered_to": [],
    "read_by": []
  },
  "created_at": "2026-01-19T02:00:00Z",
  "is_deleted": false
}
```

---

### GET /messages/conversations/{conversation_id}/messages
Get messages in a conversation.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of messages to return
- `before` (optional): Message ID for pagination (get messages before this)

**Response:** `200 OK`
```json
{
  "messages": [
    {
      "id": "507f1f77bcf86cd799439014",
      "conversation_id": "507f1f77bcf86cd799439013",
      "sender_id": "507f1f77bcf86cd799439011",
      "encrypted_content": "...",
      "content_type": "text",
      "recipient_keys": [...],
      "metadata": {...},
      "status": {...},
      "created_at": "2026-01-19T02:00:00Z",
      "is_deleted": false
    }
  ],
  "has_more": true,
  "total": 100
}
```

---

### POST /messages/{message_id}/read
Mark a message as read.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response:** `200 OK`
```json
{
  "message": "Message marked as read"
}
```

---

### DELETE /messages/{message_id}
Delete a message.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Request:**
```json
{
  "delete_for_everyone": false
}
```

**Notes:**
- `delete_for_everyone: true` - Only sender can do this, within 1 hour of sending
- `delete_for_everyone: false` - Delete only for current user

**Response:** `200 OK`
```json
{
  "message": "Message deleted for you"
}
```

---

## 🔌 WebSocket Connection

### Connection URL
```
ws://localhost:8000/api/v1/ws?token=<session_token>
```

### Client → Server Events

#### typing_start
User started typing in a conversation.

```json
{
  "type": "typing_start",
  "data": {
    "conversation_id": "507f1f77bcf86cd799439013"
  }
}
```

#### typing_stop
User stopped typing.

```json
{
  "type": "typing_stop",
  "data": {
    "conversation_id": "507f1f77bcf86cd799439013"
  }
}
```

#### message_delivered
Message delivered to device.

```json
{
  "type": "message_delivered",
  "data": {
    "message_id": "507f1f77bcf86cd799439014"
  }
}
```

#### message_read
Message read by user.

```json
{
  "type": "message_read",
  "data": {
    "message_id": "507f1f77bcf86cd799439014"
  }
}
```

#### ping
Heartbeat to keep connection alive.

```json
{
  "type": "ping"
}
```

---

### Server → Client Events

#### authenticated
Connection established successfully.

```json
{
  "type": "authenticated",
  "data": {
    "user_id": "507f1f77bcf86cd799439011",
    "connected_at": "2026-01-19T02:00:00Z"
  }
}
```

#### new_message
New message received.

```json
{
  "type": "new_message",
  "data": {
    "message": {
      "id": "507f1f77bcf86cd799439014",
      "conversation_id": "507f1f77bcf86cd799439013",
      "sender_id": "507f1f77bcf86cd799439012",
      "encrypted_content": "...",
      "content_type": "text",
      "created_at": "2026-01-19T02:00:00Z"
    }
  }
}
```

#### message_status_update
Message delivery/read status changed.

```json
{
  "type": "message_status_update",
  "data": {
    "message_id": "507f1f77bcf86cd799439014",
    "status": "read",
    "user_id": "507f1f77bcf86cd799439012",
    "timestamp": "2026-01-19T02:00:00Z"
  }
}
```

#### typing_indicator
Other user typing status.

```json
{
  "type": "typing_indicator",
  "data": {
    "conversation_id": "507f1f77bcf86cd799439013",
    "user_id": "507f1f77bcf86cd799439012",
    "is_typing": true
  }
}
```

#### message_deleted
Message deleted by sender.

```json
{
  "type": "message_deleted",
  "data": {
    "message_id": "507f1f77bcf86cd799439014",
    "deleted_for_everyone": true
  }
}
```

#### pong
Response to ping (heartbeat).

```json
{
  "type": "pong",
  "timestamp": "2026-01-19T02:00:00Z"
}
```

#### error
Error occurred.

```json
{
  "type": "error",
  "data": {
    "message": "Error description"
  }
}
```

---

## 🔒 Error Responses

All endpoints return standard error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to perform this action"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 409 Conflict
```json
{
  "detail": "Resource already exists"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred"
}
```

---

## 📊 Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/signup` | 3 requests / 15 min / IP |
| `/auth/verify-otp` | 3 attempts / session |
| `/auth/resend-otp` | 5 requests / hour / email |
| `/messages` (POST) | 100 requests / min / user |
| `/conversations` | 60 requests / min / user |
| WebSocket messages | 200 messages / min / user |

---

## 🧪 Testing with cURL

### Complete Flow Example

```bash
# 1. Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "purpose": "signup"}'

# 2. Verify OTP (check console for OTP in dev mode)
curl -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_ID", "otp": "123456"}'

# 3. Complete Signup
curl -X POST "http://localhost:8000/api/v1/auth/complete-signup?temp_token=TEMP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "mobile": "+919876543210",
    "address": "123 Test St, City 12345",
    "date_of_birth": "2000-01-01",
    "gender": "male",
    "public_key": "test_key",
    "device_info": {
      "device_id": "test-device",
      "device_name": "Test Device",
      "public_key": "test_device_key"
    }
  }'

# 4. Create Conversation
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"participant_id": "OTHER_USER_ID"}'

# 5. Send Message
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Authorization: Bearer SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "CONVERSATION_ID",
    "encrypted_content": "encrypted_blob",
    "content_type": "text",
    "recipient_keys": [...]
  }'
```

---

## 📖 Interactive Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation.
