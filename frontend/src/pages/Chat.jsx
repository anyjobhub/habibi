import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useWS } from '../contexts/WebSocketContext'
import { useEncryption } from '../hooks/useEncryption'
import api from '../utils/api'

export default function Chat() {
    const { conversationId } = useParams()
    const { user } = useAuth()
    const { lastMessage, sendMessage: sendWSMessage, usingPolling } = useWS()
    const { encrypt, decrypt } = useEncryption()

    // Search State
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [isSearching, setIsSearching] = useState(false)

    // ... (keep existing loadConversations, etc. logic)

    // Handle Search
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (searchQuery.trim().length >= 1) {
                setIsSearching(true)
                try {
                    const { data } = await api.get(`/users/search?q=${searchQuery}`)
                    setSearchResults(data.results)
                } catch (err) {
                    console.error("Search failed", err)
                } finally {
                    setIsSearching(false)
                }
            } else {
                setSearchResults([])
            }
        }, 300)

        return () => clearTimeout(timer)
    }, [searchQuery])

    const startChat = async (userId) => {
        try {
            // Optimistic check: if conversation exists in list, just go there
            const existing = conversations.find(c =>
                c.participants.some(p => p.id === userId)
            )

            if (existing) {
                setSearchQuery('')
                setSearchResults([])
                // navigate(`/chat/${existing.id}`) // Already handled by Link usually, but direct nav here if needed
                // Since this is likely a click handler on a search result not a link
                // we should navigate.
                window.location.href = `/chat/${existing.id}` // Using href to force re-render/url change if needed easily or useNavigate
                // Actually better to use navigate from hook but 'navigate' isn't explicitly defined in scope?
                // Ah, useParams is imported but not useNavigate. Let's fix that.
                return
            }

            const { data } = await api.post('/conversations', { participant_id: userId })
            setSearchQuery('')
            setSearchResults([])
            window.location.href = `/chat/${data.id}` // Force nav
        } catch (err) {
            console.error("Start chat failed", err)
            alert("Failed to start conversation")
        }
    }

    return (
        <div className="h-screen flex flex-col bg-gray-50">
            {/* ... (existing Context Menu & Modals) ... */}
            {contextMenu && (
                <div
                    className="fixed bg-white shadow-xl rounded-lg py-2 z-50 min-w-[160px] border border-gray-100"
                    style={{ top: contextMenu.y, left: contextMenu.x }}
                    onClick={(e) => e.stopPropagation()}
                >
                    <button
                        onClick={() => handleDeleteMessage(false)}
                        className="w-full text-left px-4 py-2 hover:bg-red-50 text-red-600 text-sm"
                    >
                        Delete for me
                    </button>
                    {contextMenu.message.sender_id === user.id && (
                        <button
                            onClick={() => handleDeleteMessage(true)}
                            className="w-full text-left px-4 py-2 hover:bg-red-50 text-red-600 text-sm"
                        >
                            Delete for everyone
                        </button>
                    )}
                </div>
            )}

            {/* Media Preview Modal */}
            {mediaPreview && (
                <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl max-w-lg w-full overflow-hidden">
                        <div className="p-4 border-b flex justify-between items-center">
                            <h3 className="font-bold">Send {mediaType}</h3>
                            <button onClick={clearMedia} className="text-gray-500 hover:text-gray-700">✕</button>
                        </div>
                        <div className="p-4 bg-gray-100 flex justify-center">
                            {mediaType === 'video' ? (
                                <video src={mediaPreview} controls className="max-h-[60vh]" />
                            ) : (
                                <img src={mediaPreview} alt="Preview" className="max-h-[60vh] object-contain" />
                            )}
                        </div>
                        <div className="p-4 flex gap-2">
                            <input
                                type="text"
                                className="input flex-1"
                                placeholder="Add a caption... (optional, sent as text)"
                                value={newMessage}
                                onChange={(e) => setNewMessage(e.target.value)}
                            />
                            <button
                                onClick={sendMessage}
                                className="btn btn-primary px-6"
                                disabled={sending}
                            >
                                {sending ? 'Sending...' : 'Send'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between z-10">
                <Link to="/" className="text-primary font-bold text-xl">← HABIBTI</Link>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full animate-pulse ${usingPolling ? 'bg-yellow-500' : 'bg-green-500'}`} title={usingPolling ? "Polling Mode (Fallback)" : "Real-time (Active)"}></div>
                    <h2 className="font-semibold">Chat</h2>
                </div>
                <div className="w-20"></div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Conversations List (Hidden on mobile) */}
                <div className="w-80 bg-white border-r overflow-y-auto hidden md:flex flex-col">
                    {/* Search Bar */}
                    <div className="p-4 border-b">
                        <input
                            type="text"
                            className="input w-full"
                            placeholder="Find people..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    {/* Results or List */}
                    {searchQuery ? (
                        <div className="flex-1 overflow-y-auto">
                            {isSearching ? (
                                <p className="p-4 text-center text-gray-500">Searching...</p>
                            ) : searchResults.length > 0 ? (
                                searchResults.map(u => (
                                    <div
                                        key={u.id}
                                        onClick={() => startChat(u.id)}
                                        className="p-4 border-b hover:bg-gray-50 cursor-pointer flex items-center gap-3"
                                    >
                                        <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center overflow-hidden">
                                            {u.avatar_url ? (
                                                <img src={u.avatar_url} alt="" className="w-full h-full object-cover" />
                                            ) : (
                                                <span className="text-primary font-bold">{u.username[0].toUpperCase()}</span>
                                            )}
                                        </div>
                                        <div>
                                            <p className="font-semibold">{u.full_name}</p>
                                            <p className="text-xs text-gray-500">@{u.username}</p>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p className="p-4 text-center text-gray-500">No users found</p>
                            )}
                        </div>
                    ) : (
                        <div className="flex-1 overflow-y-auto">
                            {conversations.map((conv) => {
                                const other = conv.participants.find(p => p.id !== user.id) || conv.participants[0]
                                return (
                                    <Link
                                        key={conv.id}
                                        to={`/chat/${conv.id}`}
                                        className={`block p-4 border-b hover:bg-gray-50 ${conversationId === conv.id ? 'bg-gray-100' : ''}`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="relative">
                                                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center overflow-hidden">
                                                    {other?.avatar_url ? (
                                                        <img src={other.avatar_url} alt="" className="w-full h-full object-cover" />
                                                    ) : (
                                                        <span className="text-primary font-semibold">
                                                            {other?.full_name?.charAt(0) || '?'}
                                                        </span>
                                                    )}
                                                </div>
                                                {other?.is_online && (
                                                    <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                                                )}
                                            </div>
                                            <div className="overflow-hidden">
                                                <h4 className="font-semibold truncate">{other?.full_name}</h4>
                                                <p className="text-sm text-gray-500 truncate">@{other?.username}</p>
                                            </div>
                                        </div>
                                    </Link>
                                )
                            })}
                        </div>
                    )}
                </div>

                {/* Messages Area */}
                <div className="flex-1 flex flex-col relative w-full">
                    {conversationId ? (
                        <>
                            <div className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col-reverse">
                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={`flex ${msg.sender_id === user.id ? 'justify-end' : 'justify-start'}`}
                                        onContextMenu={(e) => handleContextMenu(e, msg)}
                                    >
                                        <div
                                            className={`max-w-[75%] px-4 py-2 rounded-2xl relative group ${msg.sender_id === user.id
                                                ? 'bg-primary text-white rounded-br-none'
                                                : 'bg-white border rounded-bl-none shadow-sm'
                                                }`}
                                        >
                                            <DecryptedMessage message={msg} />
                                            <div className={`text-[10px] mt-1 text-right ${msg.sender_id === user.id ? 'text-primary-100' : 'text-gray-400'}`}>
                                                {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                {msg.status?.read_by?.length > 0 && msg.sender_id === user.id && (
                                                    <span className="ml-1">✓✓</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Typing Indicator & Input */}
                            <div className="p-4 bg-white border-t relative">
                                {typingUsers.size > 0 && (
                                    <div className="absolute -top-6 left-4 text-xs text-gray-500 italic animate-pulse">
                                        {getTypingText()}
                                    </div>
                                )}
                                <form onSubmit={sendMessage} className="flex gap-2 items-end">
                                    {/* Attachment Button */}
                                    <div className="relative">
                                        <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setShowAttach(!showAttach); }}
                                            className="btn btn-ghost rounded-full w-10 h-10 p-0 flex items-center justify-center text-gray-500 hover:bg-gray-100"
                                        >
                                            📎
                                        </button>
                                        {showAttach && (
                                            <div className="absolute bottom-12 left-0 bg-white shadow-lg rounded-xl p-2 border min-w-[150px] animate-in slide-in-from-bottom-2">
                                                <button
                                                    type="button"
                                                    className="w-full text-left px-4 py-2 hover:bg-gray-50 rounded-lg flex items-center gap-2"
                                                    onClick={() => fileInputRef.current?.click()}
                                                >
                                                    <span>📷</span> Photo / Video
                                                </button>
                                            </div>
                                        )}
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            className="hidden"
                                            accept="image/*,video/*"
                                            onChange={handleFileSelect}
                                        />
                                    </div>

                                    <textarea
                                        className="input flex-1 rounded-2xl py-2 px-4 min-h-[44px] max-h-32 resize-none"
                                        rows={1}
                                        placeholder="Message..."
                                        value={newMessage}
                                        onChange={handleTyping}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault()
                                                sendMessage()
                                            }
                                        }}
                                        disabled={sending}
                                    />

                                    <button
                                        type="submit"
                                        className="btn btn-primary rounded-full w-10 h-10 p-0 flex items-center justify-center disabled:opacity-50"
                                        disabled={sending || (!newMessage.trim() && !mediaFile)}
                                    >
                                        {sending ? '...' : '➤'}
                                    </button>
                                </form>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-gray-500 bg-gray-50">
                            <div className="w-20 h-20 bg-gray-200 rounded-full mb-4 animate-pulse"></div>
                            <p>Select a conversation to start chatting</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
