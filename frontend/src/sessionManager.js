// Session management for FinanceBot
class SessionManager {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
    }

    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('financebot_session_id');
        if (!sessionId) {
            sessionId = this.generateSessionId();
            localStorage.setItem('financebot_session_id', sessionId);
        }
        return sessionId;
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    getSessionId() {
        return this.sessionId;
    }

    getHeaders() {
        return {
            'X-Session-ID': this.sessionId,
            'Content-Type': 'application/json'
        };
    }

    getMultipartHeaders() {
        return {
            'X-Session-ID': this.sessionId
        };
    }
}

export default new SessionManager();
