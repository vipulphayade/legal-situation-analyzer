from dataclasses import dataclass, field
from typing import List

@dataclass
class ConversationContext:
    active_issue: str = ""
    active_topic_group: str = ""
    active_issue_category: str = ""
    actors: List[str] = field(default_factory=list)
    retrieved_bylaws: List[str] = field(default_factory=list)
    followup_count: int = 0
    conversation_state: str = "active"
