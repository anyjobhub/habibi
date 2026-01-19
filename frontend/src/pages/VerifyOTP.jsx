import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../utils/api'

export default function VerifyOTP() {
    const [otp, setOtp] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [resending, setResending] = useState(false)
    const navigate = useNavigate()

    const sessionId = sessionStorage.getItem('otp_session_id')
    const email = sessionStorage.getItem('email')

    useEffect(() => {
        if (!sessionId || !email) {
            navigate('/signup')
        }
    }, [sessionId, email, navigate])

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const response = await api.post('/auth/verify-otp', {
                session_id: sessionId,
                otp
            })

            if (response.data.verified) {
                sessionStorage.setItem('temp_token', response.data.temp_token)
                navigate('/complete-profile')
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Invalid OTP')
        } finally {
            setLoading(false)
        }
    }

    const handleResend = async () => {
        setResending(true)
        setError('')

        try {
            const response = await api.post('/auth/resend-otp', {
                email,
                purpose: 'signup'
            })
            sessionStorage.setItem('otp_session_id', response.data.session_id)
            alert('OTP resent successfully!')
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to resend OTP')
        } finally {
            setResending(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary to-primary-dark p-4">
            <div className="card max-w-md w-full">
                <h2 className="text-2xl font-bold mb-2">Verify OTP</h2>
                <p className="text-gray-600 mb-6">
                    Enter the 6-digit code sent to {email}
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <input
                            type="text"
                            className="input text-center text-2xl tracking-widest"
                            placeholder="000000"
                            value={otp}
                            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            maxLength={6}
                            required
                        />
                    </div>

                    {error && (
                        <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading || otp.length !== 6}
                    >
                        {loading ? 'Verifying...' : 'Verify'}
                    </button>

                    <button
                        type="button"
                        onClick={handleResend}
                        className="btn btn-secondary w-full"
                        disabled={resending}
                    >
                        {resending ? 'Resending...' : 'Resend OTP'}
                    </button>
                </form>
            </div>
        </div>
    )
}
