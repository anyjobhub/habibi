// Web Crypto API utilities for E2E encryption

// Generate RSA-OAEP key pair for user identity
export async function generateKeyPair() {
    return await window.crypto.subtle.generateKey(
        {
            name: "RSA-OAEP",
            modulusLength: 2048,
            publicExponent: new Uint8Array([1, 0, 1]),
            hash: "SHA-256",
        },
        true,
        ["encrypt", "decrypt"]
    )
}

// Export key to PEM format (for storage/server)
export async function exportKey(key) {
    const exported = await window.crypto.subtle.exportKey(
        key.type === "public" ? "spki" : "pkcs8",
        key
    )
    return arrayBufferToBase64(exported)
}

// Import key from PEM format
export async function importKey(pem, type) {
    const binaryDer = base64ToArrayBuffer(pem)
    return await window.crypto.subtle.importKey(
        type === "public" ? "spki" : "pkcs8",
        binaryDer,
        {
            name: "RSA-OAEP",
            hash: "SHA-256",
        },
        true,
        type === "public" ? ["encrypt"] : ["decrypt"]
    )
}

// Encrypt message for a recipient
export async function encryptMessage(message, recipientPublicKeyPem) {
    try {
        const publicKey = await importKey(recipientPublicKeyPem, "public")
        const symmetricKey = await window.crypto.subtle.generateKey(
            { name: "AES-GCM", length: 256 },
            true,
            ["encrypt", "decrypt"]
        )

        const encoder = new TextEncoder()
        const data = encoder.encode(message)
        const iv = window.crypto.getRandomValues(new Uint8Array(12))

        const encryptedContent = await window.crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv },
            symmetricKey,
            data
        )

        const rawSymmetricKey = await window.crypto.subtle.exportKey("raw", symmetricKey)
        const encryptedKey = await window.crypto.subtle.encrypt(
            { name: "RSA-OAEP" },
            publicKey,
            rawSymmetricKey
        )

        return {
            content: arrayBufferToBase64(encryptedContent),
            iv: arrayBufferToBase64(iv),
            key: arrayBufferToBase64(encryptedKey)
        }
    } catch (error) {
        console.error("Encryption failed:", error)
        throw error
    }
}

// New Helpers for Multi-Recipient
export async function generateSymmetricKey() {
    return await window.crypto.subtle.generateKey(
        { name: "AES-GCM", length: 256 },
        true,
        ["encrypt", "decrypt"]
    )
}

export async function encryptWithSymmetric(message, symmetricKey) {
    const encoder = new TextEncoder()
    const data = encoder.encode(message)
    const iv = window.crypto.getRandomValues(new Uint8Array(12))

    const encryptedContent = await window.crypto.subtle.encrypt(
        { name: "AES-GCM", iv: iv },
        symmetricKey,
        data
    )
    return {
        content: arrayBufferToBase64(encryptedContent),
        iv: arrayBufferToBase64(iv)
    }
}

export async function encryptSymmetricKey(symmetricKey, publicKeyPem) {
    const publicKey = await importKey(publicKeyPem, "public")
    const rawSymmetricKey = await window.crypto.subtle.exportKey("raw", symmetricKey)
    return arrayBufferToBase64(await window.crypto.subtle.encrypt(
        { name: "RSA-OAEP" },
        publicKey,
        rawSymmetricKey
    ))
}

// Decrypt message
export async function decryptMessage(encryptedPackage, privateKey, recipientKeys = [], userId = null) {
    try {
        let { content, iv, key } = encryptedPackage

        // Strategy upgrade: Look for MY key in recipientKeys if legacy 'key' is missing or we want to prefer it
        if ((!key || recipientKeys.length > 0) && userId) {
            const myKeyEntry = recipientKeys.find(k => k.user_id === userId)
            if (myKeyEntry) {
                key = myKeyEntry.encrypted_key
            }
        }

        if (!key) throw new Error("No encrypted key found for this user")

        // 1. Decrypt the symmetric key using private key
        const decryptedKeyRaw = await window.crypto.subtle.decrypt(
            { name: "RSA-OAEP" },
            privateKey,
            base64ToArrayBuffer(key)
        )

        // 2. Import the symmetric key
        const symmetricKey = await window.crypto.subtle.importKey(
            "raw",
            decryptedKeyRaw,
            { name: "AES-GCM" },
            true,
            ["encrypt", "decrypt"]
        )

        // 3. Decrypt the content
        const decryptedContent = await window.crypto.subtle.decrypt(
            { name: "AES-GCM", iv: base64ToArrayBuffer(iv) },
            symmetricKey,
            base64ToArrayBuffer(content)
        )

        const decoder = new TextDecoder()
        return decoder.decode(decryptedContent)
    } catch (error) {
        console.error("Decryption failed:", error)
        throw error
    }
}

// Helpers
function arrayBufferToBase64(buffer) {
    let binary = ''
    const bytes = new Uint8Array(buffer)
    const len = bytes.byteLength
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i])
    }
    return window.btoa(binary)
}

function base64ToArrayBuffer(base64) {
    if (!base64 || typeof base64 !== 'string') return new ArrayBuffer(0)
    try {
        const binary_string = window.atob(base64)
        const len = binary_string.length
        const bytes = new Uint8Array(len)
        for (let i = 0; i < len; i++) {
            bytes[i] = binary_string.charCodeAt(i)
        }
        return bytes.buffer
    } catch (e) {
        console.error("Invalid base64", e)
        return new ArrayBuffer(0)
    }
}
