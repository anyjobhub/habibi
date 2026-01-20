import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import api from '../utils/api'

export default function Login() {
    const [loginMethod, setLoginMethod] = useState('password') // 'password' or 'otp'
    const [identifier, setIdentifier] = useState('') // Email or Username
    const [password, setPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()
    const { login } = useAuth() // Assuming useAuth hook exposes login method

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            if (loginMethod === 'password') {
                // Password Login
                const response = await api.post('/auth/login-password', {
                    identifier,
                    password
                })

                // Login user via context provided auth method (stores token, etc.)
                // Assuming response.data follows AuthResponse structure { user, access_token, ... }
                // Use hook if available, otherwise manual set
                if (login) {
                    login(response.data.access_token, response.data.user)
                } else {
                    // Fallback if hook not ready/available in this context
                    localStorage.setItem('token', response.data.access_token)
                    localStorage.setItem('user', JSON.stringify(response.data.user))
                }
                navigate('/')
            } else {
                // OTP Login (Email only)
                if (!identifier.includes('@')) {
                    throw new Error('Please enter a valid email address for OTP login')
                }

                const response = await api.post('/auth/login', {
                    email: identifier,
                    purpose: 'login'
                })

                sessionStorage.setItem('otp_session_id', response.data.session_id)
                sessionStorage.setItem('email', identifier)
                navigate('/verify-otp')
            }
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Login failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary to-primary-dark p-4">
            <div className="card max-w-md w-full">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-primary mb-2">HABIBTI</h1>
                    <p className="text-gray-600">Privacy-First Chat</p>
                </div>

                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold">Welcome Back</h2>

                    {/* Method Toggle */}
                    <button
                        type="button"
                        onClick={() => setLoginMethod(loginMethod === 'password' ? 'otp' : 'password')}
                        className="text-sm text-primary font-medium hover:underline"
                    >
                        {loginMethod === 'password' ? 'Use OTP / Magic Link' : 'Use Password'}
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">
                            {loginMethod === 'password' ? 'Email or Username' : 'Email Address'}
                        </label>
                        <input
                            type={loginMethod === 'password' ? "text" : "email"}
                            className="input"
                            placeholder={loginMethod === 'password' ? "username or email" : "you@example.com"}
                            value={identifier}
                            onChange={(e) => setIdentifier(e.target.value)}
                            required
                        />
                    </div>

                    {loginMethod === 'password' && (
                        <div>
                            <label className="block text-sm font-medium mb-2">Password</label>
                            <input
                                type="password"
                                className="input"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading}
                    >
                        {loading
                            ? (loginMethod === 'password' ? 'Logging in...' : 'Sending OTP...')
                            : (loginMethod === 'password' ? 'Login' : 'Continue with OTP')
                        }
                    </button>
                </form>

                <p className="text-center mt-6 text-sm text-gray-600">
                    Don't have an account?{' '}
                    <Link to="/signup" className="text-primary font-medium hover:underline">
                        Sign up
                    </Link>
                </p>
            </div>
        </div>
    )
}
