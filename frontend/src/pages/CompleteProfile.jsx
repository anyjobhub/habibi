import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useEncryption } from '../hooks/useEncryption'
import api from '../utils/api'

export default function CompleteProfile() {
    const [formData, setFormData] = useState({
        username: '',
        full_name: '',
        mobile: '',
        address: '',
        date_of_birth: '',
        gender: 'prefer_not_to_say',
        bio: ''
    })
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const navigate = useNavigate()
    const { login } = useAuth()
    const { generateAndSaveKeys } = useEncryption()

    const tempToken = sessionStorage.getItem('temp_token')
    const email = sessionStorage.getItem('email')

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value })
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            // 1. Generate Encryption Keys
            const publicKeyPem = await generateAndSaveKeys()

            // 2. Submit Profile
            const response = await api.post(`/auth/complete-signup?temp_token=${tempToken}`, {
                email,
                ...formData,
                public_key: publicKeyPem,
                device_info: {
                    device_id: crypto.randomUUID(),
                    device_name: navigator.userAgent.substring(0, 50),
                    public_key: publicKeyPem // Using same key for device for now (simplified)
                }
            })

            // Clear session storage
            sessionStorage.clear()

            // Login user
            login(response.data.session_token, response.data)
            navigate('/')
        } catch (err) {
            console.error(err)
            setError(err.response?.data?.detail || 'Failed to complete profile')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary to-primary-dark p-4">
            <div className="card max-w-2xl w-full">
                <h2 className="text-2xl font-bold mb-6">Complete Your Profile</h2>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">Username *</label>
                            <input
                                type="text"
                                name="username"
                                className="input"
                                placeholder="johndoe"
                                value={formData.username}
                                onChange={handleChange}
                                pattern="[a-zA-Z0-9_]{3,30}"
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">3-30 characters, alphanumeric and underscore only</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Full Name *</label>
                            <input
                                type="text"
                                name="full_name"
                                className="input"
                                placeholder="John Doe"
                                value={formData.full_name}
                                onChange={handleChange}
                                minLength={2}
                                maxLength={100}
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Mobile Number *</label>
                            <input
                                type="tel"
                                name="mobile"
                                className="input"
                                placeholder="+919876543210"
                                value={formData.mobile}
                                onChange={handleChange}
                                pattern="\+[0-9]{10,15}"
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">E.164 format (e.g., +919876543210)</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Date of Birth *</label>
                            <input
                                type="date"
                                name="date_of_birth"
                                className="input"
                                value={formData.date_of_birth}
                                onChange={handleChange}
                                max={new Date(new Date().setFullYear(new Date().getFullYear() - 13)).toISOString().split('T')[0]}
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">Must be 13+ years old</p>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Address *</label>
                        <textarea
                            name="address"
                            className="input"
                            placeholder="123 Main St, City, State 12345"
                            value={formData.address}
                            onChange={handleChange}
                            minLength={10}
                            rows={2}
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Gender *</label>
                        <select
                            name="gender"
                            className="input"
                            value={formData.gender}
                            onChange={handleChange}
                            required
                        >
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="other">Other</option>
                            <option value="prefer_not_to_say">Prefer not to say</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Bio (Optional)</label>
                        <textarea
                            name="bio"
                            className="input"
                            placeholder="Tell us about yourself..."
                            value={formData.bio}
                            onChange={handleChange}
                            maxLength={500}
                            rows={3}
                        />
                        <p className="text-xs text-gray-500 mt-1">{formData.bio.length}/500 characters</p>
                    </div>

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
                        {loading ? 'Securing Account & Completing Signup...' : 'Complete Signup'}
                    </button>
                </form>
            </div>
        </div>
    )
}
