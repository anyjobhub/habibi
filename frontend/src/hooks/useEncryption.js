import { useState, useEffect, useCallback } from 'react'
import { generateKeyPair, exportKey, importKey, encryptMessage, decryptMessage, generateSymmetricKey, encryptWithSymmetric, encryptSymmetricKey } from '../utils/encryption'

const DB_NAME = 'HabibtiDB'
const STORE_NAME = 'keys'

export function useEncryption() {
    const [keyPair, setKeyPair] = useState(null)
    const [loading, setLoading] = useState(true)

    // Initialize DB
    const initDB = useCallback(() => {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, 1)

            request.onerror = () => reject(request.error)
            request.onsuccess = () => resolve(request.result)

            request.onupgradeneeded = (event) => {
                const db = event.target.result
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME)
                }
            }
        })
    }, [])

    // Load keys from DB
    const loadKeys = useCallback(async () => {
        try {
            const db = await initDB()
            const transaction = db.transaction(STORE_NAME, 'readonly')
            const store = transaction.objectStore(STORE_NAME)
            const request = store.get('my_keys')

            return new Promise((resolve, reject) => {
                request.onsuccess = async () => {
                    if (request.result) {
                        const { publicKeyPem, privateKeyPem } = request.result
                        const publicKey = await importKey(publicKeyPem, 'public')
                        const privateKey = await importKey(privateKeyPem, 'private')
                        setKeyPair({ publicKey, privateKey, publicKeyPem, privateKeyPem })
                        resolve(true)
                    } else {
                        resolve(false)
                    }
                    setLoading(false)
                }
                request.onerror = () => {
                    reject(request.error)
                    setLoading(false)
                }
            })
        } catch (error) {
            console.error('Failed to load keys:', error)
            setLoading(false)
            return false
        }
    }, [initDB])

    // Generate and save new keys
    const generateAndSaveKeys = useCallback(async () => {
        try {
            setLoading(true)
            const keys = await generateKeyPair()
            const publicKeyPem = await exportKey(keys.publicKey)
            const privateKeyPem = await exportKey(keys.privateKey)

            const db = await initDB()
            const transaction = db.transaction(STORE_NAME, 'readwrite')
            const store = transaction.objectStore(STORE_NAME)

            await new Promise((resolve, reject) => {
                const request = store.put({ publicKeyPem, privateKeyPem }, 'my_keys')
                request.onsuccess = () => resolve()
                request.onerror = () => reject(request.error)
            })

            setKeyPair({ ...keys, publicKeyPem, privateKeyPem })
            return publicKeyPem
        } catch (error) {
            console.error('Failed to generate keys:', error)
            throw error
        } finally {
            setLoading(false)
        }
    }, [initDB])

    useEffect(() => {
        loadKeys()
    }, [loadKeys])

    const encrypt = useCallback(async (content, recipientPublicKeyPem) => {
        return await encryptMessage(content, recipientPublicKeyPem)
    }, [])

    const decrypt = useCallback(async (encryptedPackage, recipientKeys = [], userId = null) => {
        if (!keyPair?.privateKey) throw new Error('No private key available')
        return await decryptMessage(encryptedPackage, keyPair.privateKey, recipientKeys, userId)
    }, [keyPair])

    const encryptSymmKey = useCallback(async (symmetricKey, publicKeyPem) => {
        return await encryptSymmetricKey(symmetricKey, publicKeyPem)
    }, [])

    return {
        keyPair,
        loading,
        generateAndSaveKeys,
        encrypt,
        decrypt,
        generateSymmetricKey,
        encryptWithSymmetric,
        encryptSymmetricKey: encryptSymmKey
    }
}
