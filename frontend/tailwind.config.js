/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    DEFAULT: '#667eea',
                    dark: '#764ba2',
                },
                success: '#10b981',
                danger: '#ef4444',
                warning: '#f59e0b',
                border: '#e5e7eb', // gray-200
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
