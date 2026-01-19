import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import api from '../utils/api'

export default function Profile() {
    const { user, login, logout } = useAuth()
    const [isEditing, setIsEditing] = useState(false)
    const [loading, setLoading] = useState(false)
    const [uploadingAvatar, setUploadingAvatar] = useState(false)

    // Form State
    const [formData, setFormData] = useState({
        full_name: user?.profile?.full_name || '',
        bio: user?.profile?.bio || '',
        address: user?.profile?.address || '',
        privacy: {
            discoverable_by_email: user?.privacy?.discoverable_by_email ?? true,
            discoverable_by_username: user?.privacy?.discoverable_by_username ?? true,
            show_online_status: user?.privacy?.show_online_status ?? true,
            read_receipts: user?.privacy?.read_receipts ?? true
        }
    })

    // File Input Ref
    const fileInputRef = useRef(null)

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))
    }

    const handlePrivacyChange = (e) => {
        const { name, checked } = e.target
        setFormData(prev => ({
            ...prev,
            privacy: {
                ...prev.privacy,
                [name]: checked
            }
        }))
    }

    const handleAvatarClick = () => {
        if (isEditing) {
            fileInputRef.current?.click()
        }
    }

    const handleAvatarChange = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploadingAvatar(true)
        const formData = new FormData()
        formData.append('file', file)

        try {
            const { data } = await api.post('/users/me/avatar', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            // Update local user state
            login(localStorage.getItem('token'), data)
        } catch (error) {
            console.error('Failed to upload avatar:', error)
            alert('Failed to upload avatar')
        } finally {
            setUploadingAvatar(false)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            const { data } = await api.put('/users/me', formData)
            login(localStorage.getItem('token'), data)
            setIsEditing(false)
        } catch (error) {
            console.error('Failed to update profile:', error)
            alert('Failed to update profile')
        } finally {
            setLoading(false)
        }
    }

    const toggleEdit = () => {
        if (isEditing) {
            // Cancel edit - reset form
            setFormData({
                full_name: user?.profile?.full_name || '',
                bio: user?.profile?.bio || '',
                address: user?.profile?.address || '',
                privacy: {
                    discoverable_by_email: user?.privacy?.discoverable_by_email ?? true,
                    discoverable_by_username: user?.privacy?.discoverable_by_username ?? true,
                    show_online_status: user?.privacy?.show_online_status ?? true,
                    read_receipts: user?.privacy?.read_receipts ?? true
                }
            })
        }
        setIsEditing(!isEditing)
    }

    return (
        <div className="min-h-screen bg-gray-50 pb-20">
            <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between sticky top-0 z-10">
                <Link to="/" className="text-primary font-bold text-xl">← HABIBTI</Link>
                <h2 className="font-semibold">Profile</h2>
                <button
                    onClick={toggleEdit}
                    className={`text-sm font-medium ${isEditing ? 'text-red-500' : 'text-primary'}`}
                >
                    {isEditing ? 'Cancel' : 'Edit'}
                </button>
            </header>

            <div className="max-w-2xl mx-auto p-4">
                <form onSubmit={handleSubmit} className="card">
                    {/* Avatar Section */}
                    <div className="text-center mb-8 relative">
                        <div
                            onClick={handleAvatarClick}
                            className={`w-28 h-28 mx-auto rounded-full flex items-center justify-center overflow-hidden border-4 border-white shadow-lg relative ${isEditing ? 'cursor-pointer hover:opacity-90' : ''}`}
                        >
                            {user?.profile?.avatar_url ? (
                                <img src={user.profile.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                            ) : (
                                <div className="w-full h-full bg-primary/10 flex items-center justify-center text-4xl text-primary font-bold">
                                    {user?.profile?.full_name?.charAt(0) || user?.username?.charAt(0) || '?'}
                                </div>
                            )}

                            {/* Upload Overlay */}
                            {isEditing && (
                                <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                                    <span className="text-white text-xs font-medium">
                                        {uploadingAvatar ? '...' : 'Upload'}
                                    </span>
                                </div>
                            )}
                        </div>

                        <input
                            type="file"
                            ref={fileInputRef}
                            className="hidden"
                            accept="image/*"
                            onChange={handleAvatarChange}
                        />

                        {!isEditing && (
                            <>
                                <h2 className="text-2xl font-bold mt-4">{user?.profile?.full_name}</h2>
                                <p className="text-gray-500">@{user?.username}</p>
                                {user?.profile?.bio && <p className="text-gray-600 mt-2 max-w-sm mx-auto">{user.profile.bio}</p>}
                            </>
                        )}
                    </div>

                    <div className="space-y-6">
                        {/* Basic Info */}
                        <div className="space-y-4">
                            <h3 className="font-semibold text-gray-900 border-b pb-2">Basic Info</h3>

                            <div>
                                <label className="block text-sm font-medium text-gray-600 mb-1">Full Name</label>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        name="full_name"
                                        value={formData.full_name}
                                        onChange={handleChange}
                                        className="input"
                                        required
                                    />
                                ) : (
                                    <p className="text-gray-900 font-medium">{user?.profile?.full_name}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-600 mb-1">Bio</label>
                                {isEditing ? (
                                    <textarea
                                        name="bio"
                                        value={formData.bio}
                                        onChange={handleChange}
                                        className="input"
                                        rows={3}
                                        placeholder="Tell us about yourself..."
                                    />
                                ) : (
                                    <p className="text-gray-900">{user?.profile?.bio || 'No bio set'}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-600 mb-1">Address</label>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        name="address"
                                        value={formData.address}
                                        onChange={handleChange}
                                        className="input"
                                    />
                                ) : (
                                    <p className="text-gray-900">{user?.profile?.address}</p>
                                )}
                            </div>

                            {/* Read-only fields */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-600 mb-1">Username</label>
                                    <p className="text-gray-900">@{user?.username}</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-600 mb-1">Email</label>
                                    <p className="text-gray-900 break-words">{user?.email}</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-600 mb-1">Mobile</label>
                                    <p className="text-gray-900">{user?.profile?.mobile}</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-600 mb-1">DOB</label>
                                    <p className="text-gray-900">
                                        {user?.profile?.date_of_birth && new Date(user.profile.date_of_birth).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Privacy Settings */}
                        <div className="space-y-4">
                            <h3 className="font-semibold text-gray-900 border-b pb-2">Privacy Settings</h3>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="text-sm font-medium block">Discoverable by Email</span>
                                        <span className="text-xs text-gray-500">Allow others to find you via email</span>
                                    </div>
                                    {isEditing ? (
                                        <input
                                            type="checkbox"
                                            name="discoverable_by_email"
                                            checked={formData.privacy.discoverable_by_email}
                                            onChange={handlePrivacyChange}
                                            className="w-5 h-5 text-primary rounded focus:ring-primary"
                                        />
                                    ) : (
                                        <span className={`text-sm ${user?.privacy?.discoverable_by_email ? 'text-green-600' : 'text-gray-400'}`}>
                                            {user?.privacy?.discoverable_by_email ? 'Enabled' : 'Disabled'}
                                        </span>
                                    )}
                                </div>

                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="text-sm font-medium block">Discoverable by Username</span>
                                        <span className="text-xs text-gray-500">Allow others to find you via username</span>
                                    </div>
                                    {isEditing ? (
                                        <input
                                            type="checkbox"
                                            name="discoverable_by_username"
                                            checked={formData.privacy.discoverable_by_username}
                                            onChange={handlePrivacyChange}
                                            className="w-5 h-5 text-primary rounded focus:ring-primary"
                                        />
                                    ) : (
                                        <span className={`text-sm ${user?.privacy?.discoverable_by_username ? 'text-green-600' : 'text-gray-400'}`}>
                                            {user?.privacy?.discoverable_by_username ? 'Enabled' : 'Disabled'}
                                        </span>
                                    )}
                                </div>

                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="text-sm font-medium block">Online Status</span>
                                        <span className="text-xs text-gray-500">Show when you are active</span>
                                    </div>
                                    {isEditing ? (
                                        <input
                                            type="checkbox"
                                            name="show_online_status"
                                            checked={formData.privacy.show_online_status}
                                            onChange={handlePrivacyChange}
                                            className="w-5 h-5 text-primary rounded focus:ring-primary"
                                        />
                                    ) : (
                                        <span className={`text-sm ${user?.privacy?.show_online_status ? 'text-green-600' : 'text-gray-400'}`}>
                                            {user?.privacy?.show_online_status ? 'Visible' : 'Hidden'}
                                        </span>
                                    )}
                                </div>

                                <div className="flex items-center justify-between">
                                    <div>
                                        <span className="text-sm font-medium block">Read Receipts</span>
                                        <span className="text-xs text-gray-500">Show when you've read messages</span>
                                    </div>
                                    {isEditing ? (
                                        <input
                                            type="checkbox"
                                            name="read_receipts"
                                            checked={formData.privacy.read_receipts}
                                            onChange={handlePrivacyChange}
                                            className="w-5 h-5 text-primary rounded focus:ring-primary"
                                        />
                                    ) : (
                                        <span className={`text-sm ${user?.privacy?.read_receipts ? 'text-green-600' : 'text-gray-400'}`}>
                                            {user?.privacy?.read_receipts ? 'Enabled' : 'Disabled'}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {isEditing && (
                            <button
                                type="submit"
                                className="btn btn-primary w-full"
                                disabled={loading}
                            >
                                {loading ? 'Saving Changes...' : 'Save Profile'}
                            </button>
                        )}

                        {!isEditing && (
                            <button
                                type="button"
                                onClick={logout}
                                className="btn btn-outline text-red-600 border-red-200 hover:bg-red-50 w-full"
                            >
                                Logout
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    )
}
