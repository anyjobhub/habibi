"""
OTP Service
Handles sending OTP via SMS using Twilio
"""

from twilio.rest import Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """OTP sending service"""
    
    def __init__(self):
        if settings.OTP_PROVIDER == "twilio" and settings.TWILIO_ACCOUNT_SID:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
        else:
            self.client = None
            logger.warning("Twilio not configured. OTP will be logged instead of sent.")
    
    async def send_sms(self, to: str, otp: str) -> bool:
        """
        Send OTP via SMS
        
        Args:
            to: Phone number in E.164 format
            otp: OTP code to send
            
        Returns:
            True if sent successfully
        """
        message_body = f"Your HABIBTI verification code is: {otp}\n\nThis code expires in {settings.OTP_EXPIRY_MINUTES} minutes."
        
        if self.client:
            try:
                message = self.client.messages.create(
                    body=message_body,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to
                )
                logger.info(f"OTP sent to {to}: {message.sid}")
                return True
            except Exception as e:
                logger.error(f"Failed to send OTP to {to}: {str(e)}")
                raise
        else:
            # Development mode: log OTP instead of sending
            logger.info(f"[DEV MODE] OTP for {to}: {otp}")
            print(f"\n{'='*50}")
            print(f"OTP for {to}: {otp}")
            print(f"{'='*50}\n")
            return True


# Global OTP service instance
otp_service = OTPService()


async def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via SMS"""
    return await otp_service.send_sms(phone, otp)
