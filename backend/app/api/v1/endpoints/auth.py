"""
Authentication endpoints
Handles Email OTP-based signup and login
"""

from fastapi import APIRouter, HTTPException, status, Request
from datetime import datetime, timedelta
from bson import ObjectId

from app.models import (
    OTPRequest,
    OTPResponse,
    OTPVerifyRequest,
    OTPVerifyResponse,
    UserCreate,
    UserDetailResponse
)
from app.core import (
    get_database,
    generate_otp,
    hash_otp,
    verify_otp,
    create_access_token,
    decode_access_token,
    settings
)
from app.core.rate_limit import limiter
from app.utils.sanitization import sanitize_text, sanitize_username
from app.services.email_otp_service import send_otp_email
from app.models.user import User, UserProfile, UserEncryption, UserPrivacy, Gender

router = APIRouter()


@router.post("/signup", response_model=OTPResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def signup(request: Request, data: OTPRequest):
    """
    Step 1: Initiate signup process by sending OTP to email
    
    - Validates email format
    - Checks if email already exists
    - Generates and sends OTP via email
    - Creates OTP session
    - Rate limited to 5 attempts per hour
    """
    db = await get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": data.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Please login instead."
        )
    
    # Generate OTP
    otp = generate_otp(settings.OTP_LENGTH)
    otp_hashed = hash_otp(otp)
    
    # Send OTP via Email
    try:
        await send_otp_email(data.email, otp, data.purpose)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP email: {str(e)}"
        )
    
    # Create OTP session
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    otp_session = {
        "identifier": data.email.lower(),
        "otp_hash": otp_hashed,
        "attempts": 0,
        "max_attempts": 3,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "verified": False,
        "verified_at": None,
        "session_token": None,
        "metadata": {
            "ip_address": req.client.host if req.client else None,
            "user_agent": req.headers.get("user-agent"),
            "purpose": data.purpose
        }
    }
    
    result = await db.otp_sessions.insert_one(otp_session)
    
    return OTPResponse(
        session_id=str(result.inserted_id),
        expires_in=settings.OTP_EXPIRY_MINUTES * 60,
        message=f"OTP sent successfully to {data.email}"
    )


@router.post("/login", response_model=OTPResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def login(request: Request, data: OTPRequest):
    """
    Initiate login process by sending OTP to email
    
    - Checks if user exists
    - Generates and sends OTP via email
    - Creates OTP session
    - Rate limited to 5 attempts per hour
    """
    db = await get_database()
    
    # Check if user exists
    user = await db.users.find_one({"email": data.email.lower()})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered. Please signup first."
        )
    
    # Generate OTP
    otp = generate_otp(settings.OTP_LENGTH)
    otp_hashed = hash_otp(otp)
    
    # Send OTP via Email
    try:
        await send_otp_email(data.email, otp, data.purpose)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP email: {str(e)}"
        )
    
    # Create OTP session
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    otp_session = {
        "identifier": data.email.lower(),
        "otp_hash": otp_hashed,
        "attempts": 0,
        "max_attempts": 3,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "verified": False,
        "verified_at": None,
        "session_token": None,
        "metadata": {
            "ip_address": req.client.host if req.client else None,
            "user_agent": req.headers.get("user-agent"),
            "purpose": data.purpose
        }
    }
    
    result = await db.otp_sessions.insert_one(otp_session)
    
    return OTPResponse(
        session_id=str(result.inserted_id),
        expires_in=settings.OTP_EXPIRY_MINUTES * 60,
        session_id=str(result.inserted_id),
        expires_in=settings.OTP_EXPIRY_MINUTES * 60,
        message=f"OTP sent successfully to {data.email}"
    )


@router.post("/resend-otp", response_model=OTPResponse, status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def resend_otp(request: Request, data: OTPRequest):
    """
    Resend OTP to email
    
    - Invalidates previous OTP session
    - Generates new OTP
    - Sends to email
    - Rate limited to 3 attempts per hour
    """
    db = await get_database()
    
    # Invalidate any existing unverified sessions for this email
    await db.otp_sessions.update_many(
        {
            "identifier": data.email.lower(),
            "verified": False
        },
        {
            "$set": {"expires_at": datetime.utcnow()}  # Expire immediately
        }
    )
    
    # Generate new OTP
    otp = generate_otp(settings.OTP_LENGTH)
    otp_hashed = hash_otp(otp)
    
    # Send OTP via Email
    try:
        await send_otp_email(data.email, otp, data.purpose)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP email: {str(e)}"
        )
    
    # Create new OTP session
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    otp_session = {
        "identifier": data.email.lower(),
        "otp_hash": otp_hashed,
        "attempts": 0,
        "max_attempts": 3,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "verified": False,
        "verified_at": None,
        "session_token": None,
        "metadata": {
            "ip_address": req.client.host if req.client else None,
            "user_agent": req.headers.get("user-agent"),
            "purpose": data.purpose
        }
    }
    
    result = await db.otp_sessions.insert_one(otp_session)
    
    return OTPResponse(
        session_id=str(result.inserted_id),
        expires_in=settings.OTP_EXPIRY_MINUTES * 60,
        session_id=str(result.inserted_id),
        expires_in=settings.OTP_EXPIRY_MINUTES * 60,
        message=f"OTP resent successfully to {data.email}"
    )


@router.post("/verify-otp", response_model=OTPVerifyResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_otp_endpoint(request: Request, data: OTPVerifyRequest):
    """
    Step 2: Verify OTP code
    
    - Validates OTP session
    - Checks OTP code
    - Returns temp token for signup completion
    - Rate limited to 10 attempts per minute (to prevent brute force)
    """
    db = await get_database()
    
    # Get OTP session
    try:
        session_id = ObjectId(data.session_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )
    
    otp_session = await db.otp_sessions.find_one({"_id": session_id})
    
    if not otp_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OTP session not found"
        )
    
    # Check if session expired
    if datetime.utcnow() > otp_session["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired. Please request a new one."
        )
    
    # Check if already verified
    if otp_session["verified"]:
        # Return existing temp token if still valid
        return OTPVerifyResponse(
            verified=True,
            temp_token=otp_session.get("session_token"),
            message="OTP already verified. Please complete your profile."
        )
    
    # Check attempts
    if otp_session["attempts"] >= otp_session["max_attempts"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum OTP attempts exceeded. Please request a new OTP."
        )
    
    # Verify OTP
    if not verify_otp(data.otp, otp_session["otp_hash"]):
        # Increment attempts
        await db.otp_sessions.update_one(
            {"_id": session_id},
            {"$inc": {"attempts": 1}}
        )
        
        remaining_attempts = otp_session["max_attempts"] - (otp_session["attempts"] + 1)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OTP. {remaining_attempts} attempts remaining."
        )
    
    # Mark as verified and create temp token
    temp_token = create_access_token(
        data={
            "session_id": str(session_id),
            "identifier": otp_session["identifier"],
            "purpose": otp_session["metadata"]["purpose"]
        },
        expires_delta=timedelta(minutes=15)  # 15 minutes to complete profile
    )
    
    await db.otp_sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "verified": True,
                "verified_at": datetime.utcnow(),
                "session_token": temp_token
            }
        }
    )
    
    return OTPVerifyResponse(
        verified=True,
        temp_token=temp_token,
        message="OTP verified successfully. Please complete your profile to continue."
    )


@router.post("/complete-signup", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def complete_signup(user_data: UserCreate, temp_token: str):
    """
    Step 3: Complete signup process with full profile details
    
    - Validates temp token
    - Sanitizes input (username, bio)
    - Validates all mandatory fields
    - Checks uniqueness
    - Creates user account
    """
    db = await get_database()
    
    # Sanitize inputs
    user_data.username = sanitize_username(user_data.username)
    if user_data.bio:
        user_data.bio = sanitize_text(user_data.bio)
    
    # Decode temp token
    payload = decode_access_token(temp_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please verify OTP again."
        )
    
    session_id = payload.get("session_id")
    identifier = payload.get("identifier")
    purpose = payload.get("purpose")
    
    # Verify OTP session
    try:
        otp_session = await db.otp_sessions.find_one({"_id": ObjectId(session_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session"
        )
    
    if not otp_session or not otp_session["verified"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP not verified"
        )
    
    # Check if email matches
    if user_data.email.lower() != identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email mismatch. Please use the email you verified."
        )
    
    # Check if username already taken
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken. Please choose a different username."
        )
    
    # Check if mobile number already taken
    existing_mobile = await db.users.find_one({"profile.mobile": user_data.mobile})
    if existing_mobile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mobile number already registered."
        )
    
    # Create user with complete profile
    user = User(
        email=user_data.email.lower(),
        username=user_data.username,
        profile=UserProfile(
            full_name=user_data.full_name,
            mobile=user_data.mobile,
            address=user_data.address,
            date_of_birth=user_data.date_of_birth,
            gender=user_data.gender,
            bio=user_data.bio
        ),
        privacy=UserPrivacy(),
        encryption=UserEncryption(public_key=user_data.public_key),
        devices=[user_data.device_info]
    )
    
    user_dict = user.model_dump(by_alias=True, exclude={"id"})
    result = await db.users.insert_one(user_dict)
    
    # Create session token
    session_token = create_access_token(
        data={
            "user_id": str(result.inserted_id),
            "username": user_data.username,
            "email": user_data.email.lower()
        }
    )
    
    # Get created user
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    return UserDetailResponse(
        id=str(created_user["_id"]),
        email=created_user["email"],
        username=created_user["username"],
        profile=UserProfile(**created_user["profile"]),
        privacy=UserPrivacy(**created_user["privacy"]),
        devices=created_user["devices"],
        status=created_user["status"]
    )


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user(token: str):
    """
    Get current user profile
    
    Requires valid session token
    """
    db = await get_database()
    
    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("user_id")
    
    # Get user
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserDetailResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user["username"],
        profile=UserProfile(**user["profile"]),
        privacy=UserPrivacy(**user["privacy"]),
        devices=user["devices"],
        status=user["status"]
    )
