from context_memory import ConversationContext

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def get_context(self, session_id: str):
        return self.sessions.get(session_id, ConversationContext())

    def update_context(self, session_id: str, context: ConversationContext):
        self.sessions[session_id] = context
