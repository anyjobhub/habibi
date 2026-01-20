import { useEffect } from 'react'
import { useWS } from '../contexts/WebSocketContext'
import toast, { Toaster } from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

export default function NotificationManager() {
    const { lastMessage } = useWS()
    const navigate = useNavigate()

    useEffect(() => {
        if (!lastMessage) return

        const { type, data } = lastMessage

        switch (type) {
            case 'friend_request_received':
                toast.custom((t) => (
                    <div
                        onClick={() => {
                            toast.dismiss(t.id)
                            navigate('/friends')
                        }}
                        className={`${t.visible ? 'animate-enter' : 'animate-leave'
                            } max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 cursor-pointer`}
                    >
                        <div className="flex-1 w-0 p-4">
                            <div className="flex items-start">
                                <div className="flex-shrink-0 pt-0.5">
                                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                                        {data.requester.avatar_url ? (
                                            <img
                                                className="h-10 w-10 rounded-full object-cover"
                                                src={data.requester.avatar_url}
                                                alt=""
                                            />
                                        ) : (
                                            data.requester.username[0].toUpperCase()
                                        )}
                                    </div>
                                </div>
                                <div className="ml-3 flex-1">
                                    <p className="text-sm font-medium text-gray-900">
                                        New Friend Request
                                    </p>
                                    <p className="mt-1 text-sm text-gray-500">
                                        {data.requester.full_name} (@{data.requester.username}) sent you a request
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                ))
                break

            case 'friend_request_accepted':
                toast.success(`You are now friends with a new user!`, {
                    duration: 4000,
                    icon: '🤝'
                })
                break

            case 'new_moment':
                toast.custom((t) => (
                    <div
                        onClick={() => {
                            toast.dismiss(t.id)
                            navigate('/moments')
                        }}
                        className={`${t.visible ? 'animate-enter' : 'animate-leave'
                            } max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 cursor-pointer`}
                    >
                        <div className="flex-1 w-0 p-4">
                            <div className="flex items-start">
                                <div className="flex-shrink-0 pt-0.5">
                                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-500 border-2 border-primary">
                                        {data.user.avatar_url ? (
                                            <img
                                                className="h-full w-full rounded-full object-cover"
                                                src={data.user.avatar_url}
                                                alt=""
                                            />
                                        ) : (
                                            data.user.username[0].toUpperCase()
                                        )}
                                    </div>
                                </div>
                                <div className="ml-3 flex-1">
                                    <p className="text-sm font-medium text-gray-900 border-b pb-1 mb-1">
                                        New Moment
                                    </p>
                                    <p className="text-sm text-gray-600">
                                        {data.user.full_name} shared a {data.moment_type}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                ))
                break

            default:
                break
        }
    }, [lastMessage, navigate])

    return <Toaster position="top-right" />
}
