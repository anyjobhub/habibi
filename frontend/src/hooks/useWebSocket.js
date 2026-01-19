import { useEffect, useState, useCallback, useRef } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws'

export function useWebSocket() {
    const [ws, setWs] = useState(null)
    const [connected, setConnected] = useState(false)
    const [lastMessage, setLastMessage] = useState(null)
    const reconnectTimeoutRef = useRef(null)
    const wsRef = useRef(null)

    const connect = useCallback(() => {
        const token = localStorage.getItem('token')
        if (!token) return

        try {
            const socket = new WebSocket(`${WS_URL}?token=${token}`)
            wsRef.current = socket

            socket.onopen = () => {
                console.log('WebSocket connected')
                setConnected(true)
                setWs(socket)
            }

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    setLastMessage(data)
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error)
                }
            }

            socket.onerror = (error) => {
                console.error('WebSocket error:', error)
            }

            socket.onclose = () => {
                console.log('WebSocket disconnected')
                setConnected(false)
                setWs(null)

                // Attempt to reconnect after 3 seconds
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('Attempting to reconnect...')
                    connect()
                }, 3000)
            }
        } catch (error) {
            console.error('Failed to create WebSocket:', error)
        }
    }, [])

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
        }
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }
        setWs(null)
        setConnected(false)
    }, [])

    const sendMessage = useCallback((message) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message))
        } else {
            console.warn('WebSocket is not connected')
        }
    }, [])

    useEffect(() => {
        connect()
        return () => disconnect()
    }, [connect, disconnect])

    return {
        ws,
        connected,
        lastMessage,
        sendMessage,
        reconnect: connect
    }
}
