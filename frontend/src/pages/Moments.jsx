import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import api from '../utils/api'
import { useWS } from '../contexts/WebSocketContext'

export default function Moments() {
    const [moments, setMoments] = useState([])
    const [myMoments, setMyMoments] = useState([])
    const [activeTab, setActiveTab] = useState('feed')
    const [loading, setLoading] = useState(true)
    const [showCreate, setShowCreate] = useState(false)

    // Create Mode State
    const [createType, setCreateType] = useState('text') // text, photo, video
    const [createFile, setCreateFile] = useState(null)
    const [previewUrl, setPreviewUrl] = useState(null)
    const [textContent, setTextContent] = useState('')
    const [creating, setCreating] = useState(false)
    const fileInputRef = useRef(null)
    const { lastMessage } = useWS()

    useEffect(() => {
        loadMoments()
        loadMyMoments()
    }, [])

    // Real-time updates
    useEffect(() => {
        if (lastMessage?.type === 'new_moment') {
            loadMoments()
        }
    }, [lastMessage])

    // Cleanup preview URL
    useEffect(() => {
        return () => {
            if (previewUrl && !previewUrl.startsWith('http')) {
                URL.revokeObjectURL(previewUrl)
            }
        }
    }, [previewUrl])

    const loadMoments = async () => {
        try {
            const response = await api.get('/moments')
            setMoments(response.data.moments_by_user)
        } catch (error) {
            console.error('Failed to load moments:', error)
        } finally {
            setLoading(false)
        }
    }

    const loadMyMoments = async () => {
        try {
            const response = await api.get('/moments/my')
            setMyMoments(response.data)
        } catch (error) {
            console.error('Failed to load my moments:', error)
        }
    }

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0]
        if (!file) return

        setCreateFile(file)
        const url = URL.createObjectURL(file)
        setPreviewUrl(url)
    }

    const handleCreateSubmit = async () => {
        if (!textContent && createType === 'text') {
            alert('Please enter some text')
            return
        }
        if (!createFile && createType !== 'text') {
            alert('Please select a file')
            return
        }

        setCreating(true)
        try {
            let mediaUrl = null
            let mediaThumbnail = null

            // 1. Upload media if needed
            if (createType !== 'text' && createFile) {
                const formData = new FormData()
                formData.append('file', createFile)

                const uploadRes = await api.post(`/moments/upload?type=${createType}`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                })

                mediaUrl = uploadRes.data.media_url
                mediaThumbnail = uploadRes.data.media_thumbnail
            }

            // 2. Create moment
            await api.post('/moments', {
                type: createType,
                text_content: textContent,
                media_url: mediaUrl,
                media_thumbnail: mediaThumbnail,
                duration: 5, // Default for now
                visible_to: 'friends'
            })

            // Reset and reload
            setShowCreate(false)
            setCreateFile(null)
            setPreviewUrl(null)
            setTextContent('')
            setCreateType('text')
            loadMyMoments()
            loadMoments() // Refresh feed too (might show my own?)

        } catch (error) {
            console.error('Failed to create moment:', error)
            alert('Failed to create moment. ' + (error.response?.data?.detail || ''))
        } finally {
            setCreating(false)
        }
    }

    const formatTimeRemaining = (seconds) => {
        const hours = Math.floor(seconds / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)
        return `${hours}h ${minutes}m`
    }

    return (
        <div className="min-h-screen bg-gray-50 pb-20">
            <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between sticky top-0 z-10">
                <Link to="/" className="text-primary font-bold text-xl">← HABIBTI</Link>
                <h2 className="font-semibold">Moments</h2>
                {showCreate ? (
                    <button onClick={() => setShowCreate(false)} className="text-sm font-medium text-red-500">Cancel</button>
                ) : (
                    <div className="w-12"></div>
                )}
            </header>

            <div className="max-w-2xl mx-auto p-4">
                {showCreate ? (
                    <div className="card animate-in fade-in slide-in-from-bottom-4">
                        <h3 className="font-bold text-lg mb-4">New Moment</h3>

                        <div className="flex gap-2 mb-4 p-1 bg-gray-100 rounded-lg">
                            {['text', 'photo', 'video'].map(type => (
                                <button
                                    key={type}
                                    onClick={() => {
                                        setCreateType(type)
                                        setCreateFile(null)
                                        setPreviewUrl(null)
                                    }}
                                    className={`flex-1 py-2 text-sm font-medium rounded-md capitalize transition-colors ${createType === type ? 'bg-white shadow-sm text-primary' : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                >
                                    {type}
                                </button>
                            ))}
                        </div>

                        <div className="space-y-4">
                            {/* Media Preview / Picker */}
                            {createType !== 'text' && (
                                <div
                                    className="aspect-[4/5] bg-gray-100 rounded-xl border-2 border-dashed border-gray-300 flex flex-col items-center justify-center cursor-pointer overflow-hidden relative"
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    {previewUrl ? (
                                        createType === 'video' ? (
                                            <video src={previewUrl} className="w-full h-full object-cover" controls />
                                        ) : (
                                            <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                                        )
                                    ) : (
                                        <div className="text-center p-4">
                                            <span className="text-4xl mb-2 block">📷</span>
                                            <p className="text-sm text-gray-500">Tap to select {createType}</p>
                                        </div>
                                    )}
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        className="hidden"
                                        accept={createType === 'video' ? "video/*" : "image/*"}
                                        onChange={handleFileSelect}
                                    />
                                </div>
                            )}

                            {/* Text Content */}
                            <textarea
                                className="input min-h-[100px]"
                                placeholder={createType === 'text' ? "Type something..." : "Add a caption..."}
                                value={textContent}
                                onChange={(e) => setTextContent(e.target.value)}
                                maxLength={500}
                            />

                            <button
                                onClick={handleCreateSubmit}
                                disabled={creating}
                                className="btn btn-primary w-full"
                            >
                                {creating ? 'Sharing...' : 'Share Moment'}
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Create Button */}
                        <div className="card mb-6 text-center cursor-pointer hover:bg-gray-50 transition-colors" onClick={() => setShowCreate(true)}>
                            <div className="btn btn-primary w-full pointer-events-none">
                                <span className="mr-2">+</span> Create Moment
                            </div>
                            <p className="text-sm text-gray-500 mt-2">Share a photo, video, or thought for 24 hours</p>
                        </div>

                        {/* Tabs */}
                        <div className="flex gap-4 mb-6 border-b">
                            <button
                                onClick={() => setActiveTab('feed')}
                                className={`pb-2 px-4 font-semibold transition-colors ${activeTab === 'feed'
                                    ? 'text-primary border-b-2 border-primary'
                                    : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                Friends' Moments
                            </button>
                            <button
                                onClick={() => setActiveTab('my')}
                                className={`pb-2 px-4 font-semibold transition-colors ${activeTab === 'my'
                                    ? 'text-primary border-b-2 border-primary'
                                    : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                My Moments
                            </button>
                        </div>

                        {/* Feed */}
                        {activeTab === 'feed' && (
                            <div>
                                {loading ? (
                                    <div className="text-center py-12">
                                        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                                        <p className="text-gray-500">Loading moments...</p>
                                    </div>
                                ) : moments.length === 0 ? (
                                    <div className="text-center py-12 bg-white rounded-xl border border-dashed">
                                        <p className="text-gray-500 mb-2">No moments from friends yet 😴</p>
                                        <Link to="/friends" className="text-primary font-medium hover:underline">
                                            Add friends to see their updates
                                        </Link>
                                    </div>
                                ) : (
                                    <div className="space-y-6">
                                        {moments.map((userMoments) => (
                                            <div key={userMoments.user.id} className="bg-white rounded-xl shadow-sm overflow-hidden">
                                                <div className="p-3 border-b flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-10 h-10 bg-gray-100 rounded-full overflow-hidden">
                                                            {userMoments.user.avatar_url ? (
                                                                <img src={userMoments.user.avatar_url} alt="" className="w-full h-full object-cover" />
                                                            ) : (
                                                                <div className="w-full h-full flex items-center justify-center text-primary font-bold">
                                                                    {userMoments.user.full_name?.charAt(0)}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div>
                                                            <h4 className="font-semibold text-sm">{userMoments.user.full_name}</h4>
                                                            <p className="text-xs text-gray-500">@{userMoments.user.username}</p>
                                                        </div>
                                                    </div>
                                                    {userMoments.has_unviewed && (
                                                        <span className="w-2.5 h-2.5 bg-primary rounded-full animate-pulse"></span>
                                                    )}
                                                </div>

                                                <div className="p-2 grid grid-cols-3 gap-2">
                                                    {userMoments.moments.map((moment) => (
                                                        <div
                                                            key={moment.id}
                                                            className="aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:opacity-90 relative group"
                                                        >
                                                            {moment.type === 'text' ? (
                                                                <div className="w-full h-full flex items-center justify-center p-2 bg-gradient-to-br from-primary/10 to-primary/5">
                                                                    <p className="text-[10px] text-center font-medium line-clamp-4">{moment.text_content}</p>
                                                                </div>
                                                            ) : (
                                                                moment.type === 'video' ? (
                                                                    <>
                                                                        <video src={moment.media_url} className="w-full h-full object-cover" />
                                                                        <span className="absolute top-1 right-1 text-white text-xs drop-shadow-md">▶</span>
                                                                    </>
                                                                ) : (
                                                                    <img src={moment.media_url} alt="" className="w-full h-full object-cover" />
                                                                )
                                                            )}
                                                            {!moment.has_viewed && (
                                                                <div className="absolute inset-0 ring-4 ring-inset ring-primary/50 pointer-events-none rounded-lg"></div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* My Moments */}
                        {activeTab === 'my' && (
                            <div className="grid grid-cols-2 gap-4">
                                {myMoments.map((moment) => (
                                    <div key={moment.id} className="card p-0 overflow-hidden relative">
                                        <div className="aspect-square bg-gray-100">
                                            {moment.type === 'text' ? (
                                                <div className="w-full h-full flex items-center justify-center p-4 bg-gradient-to-br from-gray-50 to-gray-100">
                                                    <p className="text-sm text-center font-medium">{moment.text_content}</p>
                                                </div>
                                            ) : (
                                                moment.type === 'video' ? (
                                                    <video src={moment.media_url} className="w-full h-full object-cover" />
                                                ) : (
                                                    <img src={moment.media_url} alt="" className="w-full h-full object-cover" />
                                                )
                                            )}
                                        </div>
                                        <div className="p-2 bg-white/90 backdrop-blur absolute bottom-0 w-full flex justify-between text-xs text-gray-600 font-medium">
                                            <span>👁 {moment.view_count}</span>
                                            <span>{formatTimeRemaining(moment.time_remaining)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    )
}
