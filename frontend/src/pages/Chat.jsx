import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useWS } from '../contexts/WebSocketContext'
import { useEncryption } from '../hooks/useEncryption'
import api from '../utils/api'

// Sub-components
const DecryptedMessage = ({ message }) => {
    const { decrypt } = useEncryption()
    const { user } = useAuth()
    const [content, setContent] = useState('Decrypting...')
    const [error, setError] = useState(false)

    useEffect(() => {
        let mounted = true
        if (!message || !user) return // Wait for user context

        const process = async () => {
            // If deleted for everyone
            if (message.is_deleted) {
                if (mounted) setContent('🚫 This message was deleted')
                return
            }

            try {
                const payload = message.encrypted_content
                let parsedPayload = payload

                // Parse if stringified JSON
                if (typeof payload === 'string') {
                    // Try parsing as JSON first (our new standard)
                    try {
                        parsedPayload = JSON.parse(payload)
                    } catch {
                        // If parse fails, assume it's legacy raw base64 string or unexpected
                        // We will let decrypt handle it or fail
                    }
                }

                const text = await decrypt(parsedPayload, message.recipient_keys, user.id)
                if (mounted) {
                    setContent(text)
                    setError(false)
                }
            } catch (err) {
                if (mounted) {
                    console.warn("Decryption failed for msg:", message.id, err)
                    setError(true)
                    setContent('')
                }
            }
        }
        process()
        return () => { mounted = false }
    }, [message, decrypt, user])

    if (error) return (
        <div className="flex items-center gap-1 text-gray-400 text-xs italic" title="Message unavailable (decryption failed)">
            <span>🔒</span>
            <span>Message unavailable</span>
        </div>
    )
    if (message.is_deleted) return <span className="text-gray-500 italic text-sm">{content}</span>

    return (
        <div className="flex flex-col gap-1">
            {/* Media Rendering */}
            {message.metadata?.media_url && (
                <div className="mb-1 overflow-hidden rounded-lg max-w-[240px]">
                    {message.metadata.file_size === -1 ? ( // Hack for video vs image if needed, or check content_type
                        message.content_type === 'video' ? (
                            <video src={message.metadata.media_url} controls className="w-full" />
                        ) : (
                            <img src={message.metadata.media_url} alt="Media" className="w-full h-auto" />
                        )
                    ) : (
                        // Fallback relying on message.content_type
                        message.content_type === 'video' ? (
                            <video src={message.metadata.media_url} controls className="w-full" />
                        ) : (
                            <img src={message.metadata.media_url} alt="Media" className="w-full h-auto" />
                        )
                    )}
                </div>
            )}
            <p className="whitespace-pre-wrap break-words text-sm md:text-base">{content}</p>
        </div>
    )
}

export default function Chat() {
    const { conversationId } = useParams()
    const { user } = useAuth()
    const { lastMessage, sendMessage: sendWSMessage, usingPolling, isConnected } = useWS()
    const { encrypt, generateSymmetricKey, encryptWithSymmetric, encryptSymmetricKey, keyPair } = useEncryption()
    const navigate = useNavigate()

    // Data State
    const [conversations, setConversations] = useState([])
    const [messages, setMessages] = useState([])
    const [loading, setLoading] = useState(true)

    // UI State
    const [newMessage, setNewMessage] = useState('')
    const [sending, setSending] = useState(false)
    const messagesEndRef = useRef(null)
    const [showAttach, setShowAttach] = useState(false)
    const fileInputRef = useRef(null)

    // Search State
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [isSearching, setIsSearching] = useState(false)

    // Typing State
    const [typingUsers, setTypingUsers] = useState(new Set())
    const typingTimeoutRef = useRef(null)

    // Media Preview State
    const [mediaFile, setMediaFile] = useState(null)
    const [mediaPreview, setPreview] = useState(null)
    const [mediaType, setMediaType] = useState('image')

    // Context Menu
    const [contextMenu, setContextMenu] = useState(null)

    // 1. Initial Load: Conversations
    useEffect(() => {
        loadConversations()
    }, [conversationId]) // Reload when switching conv (updates read status implicit)

    // 2. Initial Load: Messages (when conversationId changes)
    useEffect(() => {
        if (conversationId) {
            loadMessages(conversationId)
        } else {
            setMessages([])
        }
    }, [conversationId])

    // 3. Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // 4. REAL-TIME UPDATES (WebSocket)
    useEffect(() => {
        if (!lastMessage) return

        const { type, data } = lastMessage
        console.log('WS Event:', type, data)

        switch (type) {
            case 'new_message':
                // Only append if it belongs to current conversation
                if (data.message.conversation_id === conversationId) {
                    // Check duplicate
                    setMessages(prev => {
                        if (prev.some(m => m.id === data.message.id)) return prev
                        return [data.message, ...prev] // API returns newest first usually? 
                        // Wait, my API returns reverse chron (newest first). 
                        // But UI renders flex-col-reverse. 
                        // So index 0 is newest. 
                        // PREPENDING [data.message, ...prev] puts it at index 0 (bottom of visual list)
                    })
                    scrollToBottom()

                    // Mark as read immediately if window focused
                    api.post(`/messages/${data.message.id}/read`).catch(console.error)
                }
                // Update conversation snippet in list
                updateConversationPreview(data.message)
                break

            case 'typing_start':
                if (data.conversation_id === conversationId && data.user_id !== user.id) {
                    setTypingUsers(prev => new Set(prev).add(data.user_id))
                }
                break

            case 'typing_stop':
                if (data.conversation_id === conversationId) {
                    setTypingUsers(prev => {
                        const next = new Set(prev)
                        next.delete(data.user_id)
                        return next
                    })
                }
                break

            case 'user_online':
                updateUserStatus(data.user_id, true, data.timestamp)
                break

            case 'user_offline':
                updateUserStatus(data.user_id, false, data.timestamp)
                break

            case 'message_status_update':
                // Update read/delivered indicators
                if (conversationId) {
                    setMessages(prev => prev.map(msg =>
                        msg.id === data.message_id
                            ? { ...msg, status: { ...msg.status, read_by: [...(msg.status.read_by || []), { user_id: data.user_id }] } }
                            : msg
                    ))
                }
                break
        }
    }, [lastMessage, conversationId, user.id])

    // Helpers
    const scrollToBottom = () => {
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }

    const updateUserStatus = (userId, isOnline, timestamp = null) => {
        setConversations(prev => prev.map(conv => {
            const updatedParticipants = conv.participants.map(p =>
                p.user_id === userId ? { ...p, online: isOnline, last_seen: timestamp || p.last_seen } : p
            )
            return { ...conv, participants: updatedParticipants }
        }))
    }

    const updateConversationPreview = (message) => {
        setConversations(prev => {
            const idx = prev.findIndex(c => c.id === message.conversation_id)
            if (idx === -1) return prev // Should reload conversations actually if new

            const updated = [...prev]
            const conv = { ...updated[idx] }
            conv.last_message = {
                message_id: message.id,
                encrypted_preview: message.encrypted_content.slice(0, 50),
                timestamp: message.created_at,
                sender_id: message.sender_id
            }
            // Move to top
            updated.splice(idx, 1)
            updated.unshift(conv)
            return updated
        })
    }

    const loadConversations = async () => {
        try {
            const { data } = await api.get('/conversations')
            setConversations(data.conversations) // API returns { conversations: [], total: ... }
        } catch (err) {
            console.error(err)
        }
    }

    const loadMessages = async (id) => {
        setLoading(true)
        try {
            const { data } = await api.get(`/messages/conversations/${id}/messages`)
            // API returns desc (newest first). 
            // We want newest at bottom visually.
            // If we map normally in a col-reverse container, the first element (index 0) is at bottom.
            // So state should be [Newest, ..., Oldest]
            setMessages(data.messages)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    // Handlers
    const startChat = async (userId) => {
        try {
            const { data } = await api.post('/conversations', { participant_id: userId })
            setSearchQuery('')
            setSearchResults([])
            navigate(`/chat/${data.id}`)
        } catch (err) {
            alert("Failed to start conversation")
        }
    }

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        setMediaFile(file)
        setMediaType(file.type.startsWith('video') ? 'video' : 'image')
        setPreview(URL.createObjectURL(file))
        setShowAttach(false)
    }

    const clearMedia = () => {
        setMediaFile(null)
        setPreview(null)
        setShowAttach(false)
        if (mediaPreview) URL.revokeObjectURL(mediaPreview)
    }

    const sendMessage = async (e) => {
        e?.preventDefault()
        if ((!newMessage.trim() && !mediaFile) || sending || !conversationId) return

        // 1. Guard: Check Recipients
        const activeConv = conversations.find(c => c.id === conversationId)
        const recipient = activeConv?.participants.find(p => p.user_id !== user.id) || activeConv?.participants[0]

        // Note: We allow sending via REST even if WS is disconnected.
        // WS is for live updates. REST is for delivery.

        if (!recipient?.public_key) {
            alert("Encryption key missing for recipient. Cannot send.")
            return
        }

        setSending(true)
        try {
            let mediaUrl = null
            let mediaThumbnail = null

            // 2. Upload Media
            if (mediaFile) {
                const formData = new FormData()
                formData.append('file', mediaFile)

                // Using media upload endpoint
                const uploadRes = await api.post(`/media/upload?type=${mediaType}`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                })

                mediaUrl = uploadRes.data.url
                mediaThumbnail = mediaType === 'image' ? mediaUrl : null
            }

            // 3. Encrypt Content (AES + Multi-Recipient RSA)
            const contentToEncrypt = newMessage || (mediaFile ? '' : '')

            // A. Generate AES Key
            const symmKey = await generateSymmetricKey()

            // B. Encrypt Content with AES
            const encryptedBody = await encryptWithSymmetric(contentToEncrypt, symmKey)

            // C. Encrypt AES Key for Recipient
            const recipientEncryptedKey = await encryptSymmetricKey(symmKey, recipient.public_key)

            // D. Encrypt AES Key for Self (so we can read it later)
            // keyPair is from useEncryption hook
            let senderEncryptedKey = null
            if (keyPair?.publicKeyPem) {
                senderEncryptedKey = await encryptSymmetricKey(symmKey, keyPair.publicKeyPem)
            }

            const recipientKeys = [
                { user_id: recipient.user_id, device_id: 'web', encrypted_key: recipientEncryptedKey }
            ]
            if (senderEncryptedKey) {
                recipientKeys.push({ user_id: user.id, device_id: 'web', encrypted_key: senderEncryptedKey })
            }

            // 4. Send API
            // Note: We send encrypted_content as just { content, iv } stringified
            // The 'key' field inside encrypted_content is legacy/redundant now but we can send null or omit
            const finalPayload = {
                content: encryptedBody.content,
                iv: encryptedBody.iv,
                key: null // Legacy field, now using recipient_keys
            }

            const { data } = await api.post('/messages', {
                conversation_id: conversationId,
                encrypted_content: JSON.stringify(finalPayload),
                content_type: mediaFile ? mediaType : 'text',
                recipient_keys: recipientKeys,
                media_url: mediaUrl,
                media_thumbnail: mediaThumbnail,
                duration: null,
                file_size: mediaFile?.size || 0
            })

            // 4. Update UI
            setMessages(prev => [data, ...prev])
            setNewMessage('')
            clearMedia()

        } catch (err) {
            console.error(err)
            alert('Failed to send')
        } finally {
            setSending(false)
        }
    }

    const handleTyping = (e) => {
        setNewMessage(e.target.value)

        // Emit typing event via WS
        if (conversationId && isConnected) {
            sendWSMessage({ type: 'typing_start', conversation_id: conversationId })

            // Debounce stop
            clearTimeout(typingTimeoutRef.current)
            typingTimeoutRef.current = setTimeout(() => {
                if (isConnected) sendWSMessage({ type: 'typing_stop', conversation_id: conversationId })
            }, 2000)
        }
    }

    // Search Handler
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (searchQuery.trim().length >= 1) {
                setIsSearching(true)
                try {
                    const { data } = await api.get(`/users/search?q=${searchQuery}`)
                    setSearchResults(data.results)
                } catch (err) {
                    console.error(err)
                } finally {
                    setIsSearching(false)
                }
            } else {
                setSearchResults([])
            }
        }, 300)
        return () => clearTimeout(timer)
    }, [searchQuery])

    return (
        <div className="h-screen flex flex-col bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm px-4 py-3 flex items-center justify-between z-10">
                <Link to="/" className="text-primary font-bold text-xl">← HABIBTI</Link>
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full animate-pulse ${usingPolling ? 'bg-yellow-500' : 'bg-green-500'}`}
                        title={usingPolling ? "Polling Mode" : "Real-time"}></div>
                    <h2 className="font-semibold">Chat</h2>
                </div>
                <div className="w-20"></div>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Sidebar */}
                <div className={`w-80 bg-white border-r flex-col ${conversationId ? 'hidden md:flex' : 'flex w-full'}`}>
                    <div className="p-4 border-b">
                        <input
                            type="text"
                            className="input w-full"
                            placeholder="Find people..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {searchQuery ? (
                            searchResults.map(u => (
                                <div key={u.id} onClick={() => startChat(u.id)} className="p-4 border-b hover:bg-gray-50 cursor-pointer flex gap-3 items-center">
                                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center font-bold text-primary">
                                        {u.avatar_url ? <img src={u.avatar_url} className="w-full h-full rounded-full object-cover" /> : u.username[0]}
                                    </div>
                                    <div>
                                        <p className="font-semibold">{u.full_name}</p>
                                        <p className="text-sm text-gray-500">@{u.username}</p>
                                    </div>
                                </div>
                            ))
                        ) : (
                            conversations.map(conv => {
                                const other = conv.participants.find(p => p.user_id !== user.id) || conv.participants[0]
                                return (
                                    <div
                                        key={conv.id}
                                        onClick={() => navigate(`/chat/${conv.id}`)}
                                        className={`p-4 border-b hover:bg-gray-50 cursor-pointer flex gap-3 items-center ${conversationId === conv.id ? 'bg-indigo-50' : ''}`}
                                    >
                                        <div className="relative">
                                            <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
                                                {other.avatar_url ? <img src={other.avatar_url} className="w-full h-full object-cover" /> : <span className="font-bold text-gray-500">{other.full_name[0]}</span>}
                                            </div>
                                            {other.online && <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex justify-between items-baseline">
                                                <h4 className="font-semibold truncate">{other.full_name}</h4>
                                                {conv.last_message && (
                                                    <span className="text-xs text-gray-400">
                                                        {(() => {
                                                            let ts = conv.last_message.timestamp
                                                            if (ts && !ts.endsWith('Z') && !ts.includes('+')) ts += 'Z'
                                                            return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                                        })()}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-500 truncate">
                                                {typingUsers.has(other.user_id) ? (
                                                    <span className="text-green-600 font-medium">typing...</span>
                                                ) : (
                                                    conv.last_message ? 'Encrypted Message' : 'Start a conversation'
                                                )}
                                            </p>
                                        </div>
                                    </div>
                                )
                            })
                        )}
                    </div>
                </div>

                {/* Chat Area */}
                <div className={`flex-1 flex flex-col relative ${!conversationId ? 'hidden md:flex' : 'flex'}`}>
                    {conversationId ? (
                        <>
                            {/* Active Chat Header */}
                            <header className="bg-white px-4 py-3 border-b flex items-center justify-between shadow-sm z-20">
                                {(() => {
                                    const activeConv = conversations.find(c => c.id === conversationId)
                                    const other = activeConv?.participants.find(p => p.user_id !== user.id) || activeConv?.participants[0]

                                    if (!other) return <div>Loading...</div>

                                    return (
                                        <div className="flex items-center gap-3">
                                            <button onClick={() => navigate('/chat')} className="md:hidden text-gray-500 mr-2">←</button>
                                            <div className="relative">
                                                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                                                    {other.avatar_url ? (
                                                        <img src={other.avatar_url} className="w-full h-full object-cover" />
                                                    ) : (
                                                        <span className="font-bold text-primary">{other.full_name?.[0]}</span>
                                                    )}
                                                </div>
                                                {other.online && <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-white"></div>}
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-sm">{other.full_name}</h3>
                                                <div className="text-xs text-gray-500">
                                                    {other.online ? (
                                                        <span className="text-green-600 font-medium">Online</span>
                                                    ) : (
                                                        other.last_seen ? `Last seen: ${new Date(other.last_seen).toLocaleDateString()} ${new Date(other.last_seen).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Offline'
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })()}

                                {/* Info / Actions */}
                                <button className="p-2 text-gray-400 hover:text-gray-600">⋮</button>
                            </header>

                            <div className="flex-1 overflow-y-auto p-4 flex flex-col-reverse gap-4 bg-[#e5ded8]/30"> {/* WhatsApp-like bg hint */}
                                {messages.map(msg => (
                                    <div key={msg.id} className={`flex ${msg.sender_id === user.id ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[70%] px-4 py-2 rounded-2xl ${msg.sender_id === user.id ? 'bg-primary text-white rounded-br-none' : 'bg-white border rounded-bl-none shadow-sm'
                                            }`}>
                                            <DecryptedMessage message={msg} />
                                            <p className={`text-[10px] text-right mt-1 ${msg.sender_id === user.id ? 'text-indigo-100' : 'text-gray-400'}`}>
                                                {(() => {
                                                    let ts = msg.created_at
                                                    if (ts && !ts.endsWith('Z') && !ts.includes('+')) ts += 'Z'
                                                    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                                })()}
                                                {msg.sender_id === user.id && msg.status?.read_by?.length > 0 && <span className="ml-1">✓✓</span>}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Typing Indicator */}
                            {typingUsers.size > 0 && (
                                <div className="px-4 py-1 text-xs text-gray-500 italic">
                                    Someone is typing...
                                </div>
                            )}

                            {/* Input */}
                            <div className="p-4 bg-white border-t">
                                <form onSubmit={sendMessage} className="flex gap-2 items-center">
                                    <button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                                    >📷</button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        className="hidden"
                                        accept="image/*,video/*"
                                        onChange={handleFileSelect}
                                    />

                                    <input
                                        className="input flex-1 rounded-full px-4"
                                        placeholder="Message..."
                                        value={newMessage}
                                        onChange={handleTyping}
                                        disabled={sending}
                                    />
                                    <button
                                        type="submit"
                                        className="btn btn-primary rounded-full w-10 h-10 flex items-center justify-center p-0"
                                        disabled={sending || (!newMessage.trim() && !mediaFile)}
                                    >
                                        ➤
                                    </button>
                                </form>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-gray-400">
                            Select a conversation to start chatting
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
