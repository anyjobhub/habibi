import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../utils/api'

export default function Friends() {
    const [activeTab, setActiveTab] = useState('friends')
    const [friends, setFriends] = useState([])
    const [requests, setRequests] = useState([])
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        loadFriends()
        loadRequests()
    }, [])

    const loadFriends = async () => {
        try {
            const response = await api.get('/friends')
            setFriends(response.data.friends)
        } catch (error) {
            console.error('Failed to load friends:', error)
        }
    }

    const loadRequests = async () => {
        try {
            const response = await api.get('/friends/requests/received')
            setRequests(response.data.requests)
        } catch (error) {
            console.error('Failed to load requests:', error)
        }
    }

    const searchUsers = async (e) => {
        e.preventDefault()
        if (!searchQuery.trim()) return

        setLoading(true)
        try {
            const response = await api.get(`/users/search?q=${searchQuery}&search_by=username`)
            setSearchResults(response.data.results)
        } catch (error) {
            console.error('Search failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const sendFriendRequest = async (userId) => {
        try {
            await api.post('/friends/request', { user_id: userId })
            alert('Friend request sent!')
            setSearchResults([])
            setSearchQuery('')
        } catch (error) {
            alert(error.response?.data?.detail || 'Failed to send request')
        }
    }

    const respondToRequest = async (friendshipId, action) => {
        try {
            await api.post(`/friends/requests/${friendshipId}/respond`, { action })
            loadRequests()
            loadFriends()
        } catch (error) {
            alert('Failed to respond to request')
        }
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between">
                <Link to="/" className="text-primary font-bold text-xl">← HABIBTI</Link>
                <h2 className="font-semibold">Friends</h2>
                <div className="w-20"></div>
            </header>

            <div className="max-w-4xl mx-auto p-4">
                {/* Search */}
                <div className="card mb-6">
                    <h3 className="font-semibold mb-4">Find Friends</h3>
                    <form onSubmit={searchUsers} className="flex gap-2">
                        <input
                            type="text"
                            className="input flex-1"
                            placeholder="Search by username..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <button type="submit" className="btn btn-primary" disabled={loading}>
                            {loading ? 'Searching...' : 'Search'}
                        </button>
                    </form>

                    {searchResults.length > 0 && (
                        <div className="mt-4 space-y-2">
                            {searchResults.map((user) => (
                                <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div>
                                        <h4 className="font-semibold">{user.full_name}</h4>
                                        <p className="text-sm text-gray-600">@{user.username}</p>
                                    </div>
                                    <button
                                        onClick={() => sendFriendRequest(user.id)}
                                        className="btn btn-primary text-sm"
                                    >
                                        Add Friend
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Tabs */}
                <div className="flex gap-4 mb-6">
                    <button
                        onClick={() => setActiveTab('friends')}
                        className={`pb-2 font-semibold ${activeTab === 'friends' ? 'text-primary border-b-2 border-primary' : 'text-gray-500'}`}
                    >
                        Friends ({friends.length})
                    </button>
                    <button
                        onClick={() => setActiveTab('requests')}
                        className={`pb-2 font-semibold ${activeTab === 'requests' ? 'text-primary border-b-2 border-primary' : 'text-gray-500'}`}
                    >
                        Requests ({requests.length})
                    </button>
                </div>

                {/* Friends List */}
                {activeTab === 'friends' && (
                    <div className="card">
                        {friends.length === 0 ? (
                            <p className="text-center text-gray-500 py-8">No friends yet. Search for users above!</p>
                        ) : (
                            <div className="space-y-3">
                                {friends.map((friend) => (
                                    <div key={friend.id} className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg">
                                        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                                            <span className="text-primary font-semibold">{friend.full_name.charAt(0)}</span>
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-semibold">{friend.full_name}</h4>
                                            <p className="text-sm text-gray-600">@{friend.username}</p>
                                        </div>
                                        <Link to={`/chat`} className="btn btn-secondary text-sm">
                                            Message
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Requests List */}
                {activeTab === 'requests' && (
                    <div className="card">
                        {requests.length === 0 ? (
                            <p className="text-center text-gray-500 py-8">No pending requests</p>
                        ) : (
                            <div className="space-y-3">
                                {requests.map((request) => (
                                    <div key={request.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                                        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                                            <span className="text-primary font-semibold">{request.user.full_name.charAt(0)}</span>
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-semibold">{request.user.full_name}</h4>
                                            <p className="text-sm text-gray-600">@{request.user.username}</p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => respondToRequest(request.id, 'accept')}
                                                className="btn btn-primary text-sm"
                                            >
                                                Accept
                                            </button>
                                            <button
                                                onClick={() => respondToRequest(request.id, 'reject')}
                                                className="btn btn-secondary text-sm"
                                            >
                                                Decline
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
