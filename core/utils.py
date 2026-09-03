import re


def parse_about_content(content):
    """Splits plain-text About Us content into heading/paragraph blocks so short
    section-title lines (e.g. "Vision", "Objectives") render as real headings
    instead of getting swallowed into the following paragraph's line break.
    Shared by church/gym/aff's About Us pages so all three get the same
    sectioned styling instead of one long wall of text."""
    blocks = []
    for raw_block in re.split(r'\n\s*\n', content.strip()):
        raw_block = raw_block.strip()
        if not raw_block:
            continue
        lines = raw_block.split('\n', 1)
        first_line = lines[0].strip()
        rest = lines[1].strip() if len(lines) > 1 else ''
        looks_like_heading = len(first_line) <= 60 and not first_line.endswith(('.', '!', '?', ':'))
        if looks_like_heading and (rest or len(lines) == 1):
            blocks.append({'type': 'heading', 'text': first_line})
            if rest:
                blocks.append({'type': 'paragraph', 'text': rest})
        else:
            blocks.append({'type': 'paragraph', 'text': raw_block})
    return blocks
