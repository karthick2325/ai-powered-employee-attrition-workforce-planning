/**
 * Workforce Intelligence — API Client
 */
const API = {
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
                url.searchParams.append(key, params[key]);
            }
        });
        
        try {
            const res = await fetch(url.toString(), {
                headers: { 'Accept': 'application/json' }
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `HTTP error ${res.status}`);
            }
            return await res.json();
        } catch (error) {
            console.error(`API GET ${endpoint} failed:`, error);
            throw error;
        }
    },

    async post(endpoint, data = {}) {
        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `HTTP error ${res.status}`);
            }
            return await res.json();
        } catch (error) {
            console.error(`API POST ${endpoint} failed:`, error);
            throw error;
        }
    }
};
