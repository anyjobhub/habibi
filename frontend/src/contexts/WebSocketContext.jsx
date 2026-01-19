import { createContext, useContext, useEffect, useState, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'

const WebSocketContext = createContext(null)

export const WebSocketProvider = ({ children }) => {
    const { token } = useAuth()
    const [lastMessage, setLastMessage] = useState(null)
    const [isConnected, setIsConnected] = useState(false)
    const [connectError, setConnectError] = useState(null)
    const [usingPolling, setUsingPolling] = useState(false)

    // Connection Logic
    const wsRef = useRef(null)
    const reconnectTimeoutRef = useRef(null)
    const pollingIntervalRef = useRef(null)
    const reconnectAttempts = useRef(0)

    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws'

    useEffect(() => {
        if (token) {
            connect()
        } else {
            cleanup()
        }

        return cleanup
    }, [token])

    const cleanup = () => {
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }
        clearTimeout(reconnectTimeoutRef.current)
        stopPolling()
        setIsConnected(false)
        setUsingPolling(false)
    }

    const connect = () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        try {
            const ws = new WebSocket(`${WS_URL}?token=${token}`)
            wsRef.current = ws

            ws.onopen = () => {
                console.log('WS Connected')
                setIsConnected(true)
                setConnectError(null)
                setUsingPolling(false)
                stopPolling()
                reconnectAttempts.current = 0
            }

            ws.onclose = () => {
                console.log('WS Disconnected')
                setIsConnected(false)
                handleDisconnect()
            }

            ws.onerror = (error) => {
                console.error('WS Error:', error)
                setConnectError('Connection error')
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    setLastMessage(data)
                } catch (err) {
                    console.error('Failed to parse WS message', err)
                }
            }

        } catch (err) {
            console.error('Failed to create WebSocket', err)
            handleDisconnect()
        }
    }

    const handleDisconnect = () => {
        // 1. Activate Polling immediately
        startPolling()

        // 2. Schedule WS Reconnect (Exponential Backoff)
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        reconnectAttempts.current += 1

        console.log(`Scheduling reconnect in ${delay}ms...`)
        reconnectTimeoutRef.current = setTimeout(() => {
            connect()
        }, delay)
    }

    // Polling Strategy
    const startPolling = () => {
        if (pollingIntervalRef.current) return // Already polling

        console.log('Activating HTTP Polling Fallback 🟡')
        setUsingPolling(true)

        // Poll every 30 seconds
        pollingIntervalRef.current = setInterval(() => {
            // In a real generic context, we can't easily poll "current conversation" messages 
            // without knowing ID. 
            // ideally we'd trigger a global event or the consumers would poll.
            // But for this "Context" to handle it, we emit a "POLL_TRIGGER" event 
            // that components can listen to?

            // Or simpler: Just update 'lastMessage' with type 'polling_trigger'
            // so Chat.jsx knows it should fetch.
            setLastMessage({ type: 'polling_trigger', timestamp: Date.now() })
        }, 30000)
    }

    const stopPolling = () => {
        if (pollingIntervalRef.current) {
            console.log('Stopping Polling (WS Restored) 🟢')
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
        }
    }

    const sendMessage = (data) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data))
        } else {
            console.warn('WS not connected, cannot send message via WS')
            // Chat.jsx handles fallback to API for sending messages
        }
    }

    return (
        <WebSocketContext.Provider value={{
            lastMessage,
            sendMessage,
            isConnected,
            usingPolling
        }}>
            {children}
        </WebSocketContext.Provider>
    )
}

export const useWS = () => useContext(WebSocketContext)
