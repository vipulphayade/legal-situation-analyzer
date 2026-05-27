def build_grounded_prompt(query: str, bylaws: list):
    sections = []

    for bylaw in bylaws[:3]:
        sections.append(
            f"""
Likely Relevant Bye-law: {bylaw.get('section')}

Why matched:
{bylaw.get('why_this_applies')}

Simple explanation:
{bylaw.get('plain_english')}

Practical guidance:
{bylaw.get('practical_guidance')}
"""
        )

    return "\n".join(sections)
