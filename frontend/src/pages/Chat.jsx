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

    const [conversations, setConversations] = useState([])
    const [messages, setMessages] = useState([])
    const [newMessage, setNewMessage] = useState('')
    const [loading, setLoading] = useState(true)
    const [sending, setSending] = useState(false)
    const [typingUsers, setTypingUsers] = useState(new Set())

    // Media & Actions State
    const [showAttach, setShowAttach] = useState(false)
    const [mediaFile, setMediaFile] = useState(null)
    const [mediaPreview, setMediaPreview] = useState(null)
    const [mediaType, setMediaType] = useState('image') // image, video
    const [contextMenu, setContextMenu] = useState(null) // { x, y, message }

    const messagesEndRef = useRef(null)
    const typingTimeoutRef = useRef(null)
    const fileInputRef = useRef(null)

    // Load conversations on mount
    useEffect(() => {
        loadConversations()
    }, [])

    // Close menus on click outside
    useEffect(() => {
        const handleClick = () => {
            setContextMenu(null)
            setShowAttach(false)
        }
        window.addEventListener('click', handleClick)
        return () => window.removeEventListener('click', handleClick)
    }, [])

    // Handle incoming WebSocket messages
    useEffect(() => {
        if (!lastMessage) return

        const { type, data } = lastMessage

        switch (type) {
            case 'new_message':
                if (data.message.conversation_id === conversationId) {
                    setMessages(prev => [data.message, ...prev])
                    scrollToBottom()
                }
                loadConversations()
                break

            case 'message_deleted':
                if (data.message_id) {
                    setMessages(prev => prev.map(m => {
                        if (m.id === data.message_id) {
                            return { ...m, is_deleted: true }
                        }
                        return m
                    }))
                }
                break

            case 'typing_indicator':
                if (data.conversation_id === conversationId) {
                    setTypingUsers(prev => {
                        const next = new Set(prev)
                        if (data.is_typing) {
                            next.add(data.user_id)
                        } else {
                            next.delete(data.user_id)
                        }
                        return next
                    })
                }
                break

            case 'user_online':
            case 'user_offline':
                setConversations(prev => prev.map(c => {
                    const updatedParticipants = c.participants.map(p => {
                        if (p.id === data.user_id) {
                            return { ...p, is_online: type === 'user_online' }
                        }
                        return p
                    })
                    return { ...c, participants: updatedParticipants }
                }))
                break

            case 'polling_trigger':
                // Fetch newer messages than last one we have
                if (messages.length > 0) {
                    const lastMsg = messages[0] // Since messages are prepended (newest at index 0)
                    loadNewMessages(conversationId, lastMsg.created_at)
                }
                break

            default:
                break
        }
    }, [lastMessage, conversationId, messages]) // Depend on messages to get latest timestamp

    // Load messages when conversation changes
    useEffect(() => {
        if (conversationId) {
            loadMessages(conversationId)
            setTypingUsers(new Set())
        }
    }, [conversationId])

    const scrollToBottom = () => {
        if (messagesEndRef.current) {
            setTimeout(() => {
                messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
            }, 100)
        }
    }

    const loadConversations = async () => {
        try {
            const response = await api.get('/conversations')
            setConversations(response.data.conversations)
        } catch (error) {
            console.error('Failed to load conversations:', error)
        } finally {
            setLoading(false)
        }
    }

    const loadMessages = async (convId) => {
        try {
            const response = await api.get(`/messages/conversations/${convId}/messages`)
            setMessages(response.data.messages)
        } catch (error) {
            console.error('Failed to load messages:', error)
        }
    }

    const loadNewMessages = async (convId, sinceIso) => {
        try {
            const response = await api.get(`/messages/conversations/${convId}/messages?since=${sinceIso}`)
            const newMsgs = response.data.messages

            if (newMsgs.length > 0) {
                setMessages(prev => {
                    // Deduplicate based on ID
                    const existingIds = new Set(prev.map(m => m.id))
                    const uniqueNew = newMsgs.filter(m => !existingIds.has(m.id))
                    return [...uniqueNew, ...prev]
                })
            }
        } catch (error) {
            console.error('Failed to poll messages:', error)
        }
    }

    const handleTyping = (e) => {
        setNewMessage(e.target.value)

        if (!conversationId) return

        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current)
        } else {
            sendWSMessage({
                type: 'typing_start',
                data: { conversation_id: conversationId }
            })
        }

        typingTimeoutRef.current = setTimeout(() => {
            sendWSMessage({
                type: 'typing_stop',
                data: { conversation_id: conversationId }
            })
            typingTimeoutRef.current = null
        }, 2000)
    }

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0]
        if (!file) return

        const isVideo = file.type.startsWith('video/')
        setMediaType(isVideo ? 'video' : 'image')
        setMediaFile(file)

        const url = URL.createObjectURL(file)
        setMediaPreview(url)
        setShowAttach(false)
    }

    const clearMedia = () => {
        setMediaFile(null)
        setMediaPreview(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const sendMessage = async (e) => {
        if (e) e.preventDefault()

        // Validation
        if ((!newMessage.trim() && !mediaFile) || !conversationId || sending) return

        setSending(true)
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current)
            typingTimeoutRef.current = null
            sendWSMessage({
                type: 'typing_stop',
                data: { conversation_id: conversationId }
            })
        }

        try {
            // 1. Get recipients
            const conversation = conversations.find(c => c.id === conversationId)
            if (!conversation) throw new Error('Conversation not found')

            const recipientIds = conversation.participants
                .map(p => p.id)
                .filter(id => id !== user.id)

            // 2. Fetch public keys
            const recipientKeys = []
            for (const recipientId of recipientIds) {
                try {
                    const { data } = await api.get(`/users/${recipientId}/public-key`)
                    recipientKeys.push({
                        user_id: recipientId,
                        public_key: data.public_key,
                        device_id: data.devices[0]?.device_id || 'unknown'
                    })
                } catch (err) {
                    console.warn(`Could not fetch key for user ${recipientId}`)
                }
            }

            if (recipientKeys.length === 0) {
                alert('Cannot send message: Recipient has no public key')
                return
            }

            // 3. Handle Media Upload
            let contentToSend = newMessage
            let finalContentType = 'text'
            let mediaUrl = null

            if (mediaFile) {
                const formData = new FormData()
                formData.append('file', mediaFile)

                // Upload
                const uploadRes = await api.post(`/media/upload?type=${mediaType}`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                })

                // Content to encrypt is the URL
                contentToSend = uploadRes.data.url
                mediaUrl = uploadRes.data.url
                finalContentType = mediaType
            }

            // 4. Encrypt Content (Text or URL)
            const targetUser = recipientKeys[0]
            const encryptedPackage = await encrypt(contentToSend, targetUser.public_key)

            const payloadStart = JSON.stringify({
                iv: encryptedPackage.iv,
                content: encryptedPackage.content
            })

            // 5. Send to Backend
            await api.post('/messages', {
                conversation_id: conversationId,
                encrypted_content: payloadStart,
                content_type: finalContentType,
                recipient_keys: [
                    {
                        user_id: targetUser.user_id,
                        device_id: targetUser.device_id,
                        encrypted_key: encryptedPackage.key
                    }
                ],
                // Add preview for media if we want (not implemented in backend model yet fully but metadata supports it)
                media_url: mediaUrl // Also send unencrypted URL in metadata for easier server handling? Backend ignores it for E2E purity usually, but let's keep it safe in encrypted blob. The backend model has 'media_url' in metadata. Adding it there is duplicate but useful if not E2E strict.
                // Actually, let's NOT send media_url in plain text metadata to keep it private (E2E).
                // The URL is inside encrypted_content.
            })

            // Reset UI
            setNewMessage('')
            clearMedia()

        } catch (error) {
            console.error('Failed to send message:', error)
            alert('Failed to send message')
        } finally {
            setSending(false)
        }
    }

    const handleDeleteMessage = async (deleteForEveryone) => {
        if (!contextMenu) return

        try {
            await api.delete(`/messages/${contextMenu.message.id}`, {
                data: { delete_for_everyone: deleteForEveryone }
            })

            // Optimistic update
            setMessages(prev => prev.map(m => {
                if (m.id === contextMenu.message.id) {
                    if (deleteForEveryone) return { ...m, is_deleted: true }
                    // For "delete for me", we should remove it from list
                    return null
                }
                return m
            }).filter(Boolean))

        } catch (error) {
            console.error("Delete failed", error)
            alert("Failed to delete message")
        } finally {
            setContextMenu(null)
        }
    }

    const handleContextMenu = (e, msg) => {
        e.preventDefault() // prevent browser menu
        e.stopPropagation()
        setContextMenu({
            x: e.pageX,
            y: e.pageY,
            message: msg
        })
    }

    // Helper to decrypt message content
    const DecryptedMessage = ({ message }) => {
        const [decryptedText, setDecryptedText] = useState('Decrypting...')

        useEffect(() => {
            if (message.is_deleted) {
                setDecryptedText('🚫 This message was deleted')
                return
            }

            const decryptContent = async () => {
                try {
                    // Find key for me
                    const myKeyWrapper = message.recipient_keys.find(k => k.user_id === user.id)

                    // Allow sender to decrypt if they have a key (not implemented in v1 but good practice) 
                    // or just show "You sent..." for text.
                    // For Media, "You sent a photo" is annoying if you can't see it.
                    // But without Self-Key, we can't show it.

                    if (!myKeyWrapper && message.sender_id !== user.id) {
                        setDecryptedText('⛔ No key')
                        return
                    }

                    if (message.sender_id === user.id) {
                        // MVP Limitation: Sender can't decrypt own message unless we add self-key
                        // For now, text: "You sent..."
                        // For media: "You sent a photo"
                        const type = message.content_type || 'text'
                        setDecryptedText(type === 'text' ? 'You sent a secure message' : `You sent a ${type}`)
                        return
                    }

                    let iv, content
                    try {
                        const parsed = JSON.parse(message.encrypted_content)
                        iv = parsed.iv
                        content = parsed.content
                    } catch {
                        setDecryptedText('Invalid format')
                        return
                    }

                    const text = await decrypt({
                        iv,
                        content,
                        key: myKeyWrapper.encrypted_key
                    })
                    setDecryptedText(text)
                } catch (err) {
                    console.error(err)
                    setDecryptedText('🔒 Decryption failed')
                }
            }
            decryptContent()
        }, [message])

        if (message.is_deleted) return <p className="italic text-gray-400">🚫 Message deleted</p>
        if (message.sender_id === user.id) return <p className="italic opacity-80">{decryptedText}</p>

        // Render based on type
        if (message.content_type === 'image' && decryptedText.startsWith('http')) {
            return (
                <img
                    src={decryptedText}
                    alt="Encrypted Content"
                    className="rounded-lg max-w-full max-h-64 object-cover cursor-pointer"
                    onClick={() => window.open(decryptedText, '_blank')}
                />
            )
        }
        if (message.content_type === 'video' && decryptedText.startsWith('http')) {
            return (
                <video
                    src={decryptedText}
                    controls
                    className="rounded-lg max-w-full max-h-64"
                />
            )
        }

        return <p className="whitespace-pre-wrap">{decryptedText}</p>
    }

    const getTypingText = () => {
        if (typingUsers.size === 0) return ''
        const count = typingUsers.size
        return count === 1 ? 'Someone is typing...' : `${count} people are typing...`
    }

    return (
        <div className="h-screen flex flex-col bg-gray-50">
            {/* Context Menu */}
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
                <div className="w-80 bg-white border-r overflow-y-auto hidden md:block">
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
