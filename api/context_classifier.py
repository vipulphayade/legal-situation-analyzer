from difflib import SequenceMatcher

def classify_context_relationship(previous_topic: str, current_topic: str) -> str:
    if not previous_topic:
        return "new_scenario"

    similarity = SequenceMatcher(None, previous_topic, current_topic).ratio()

    if similarity > 0.70:
        return "follow_up"

    if similarity < 0.30:
        return "unrelated"

    return "ambiguous"
