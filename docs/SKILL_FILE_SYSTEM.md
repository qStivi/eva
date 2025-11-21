# Skill File System Design

**Status:** Planned for Phase 2-3 implementation
**Purpose:** Modular, token-efficient prompt management inspired by Claude Code
**Last Updated:** 2025-11-13

---

## Overview

Eva uses a **skill file system** to separate character personality from capability documentation. This approach is inspired by Claude Code's skill system and provides significant advantages over monolithic system prompts.

## The Problem with Monolithic Prompts

A single system prompt containing everything becomes unwieldy:

```
[Character personality: 2000 tokens]
[Memory system explanation: 500 tokens]
[Journal format guide: 300 tokens]
[Command documentation: 400 tokens]
[Tool usage examples: 800 tokens]
[Webhook handling: 300 tokens]
= 4300+ tokens ALWAYS loaded
```

**Issues:**
- High token cost for every request
- Difficult to maintain and update
- Hard to debug specific capabilities
- Character personality mixed with tool instructions
- Can't easily A/B test different approaches

## The Skill File Solution

**Base Character Prompt** (always loaded, ~2000 tokens):
- Who Eva is (personality, appearance, self-awareness)
- How she communicates (sass, defensiveness, hidden care)
- Core philosophy (companion, not tool)

**Skill Files** (loaded dynamically when needed):
- `journal-skill.md` - How to write Logseq journal entries
- `memory-skill.md` - How to use retrieved memories naturally
- `character-state-skill.md` - How to update/reference mood
- `webhook-skill.md` - How to react to external triggers
- `conversation-skill.md` - General conversation guidelines

**Benefits:**
- ✅ Token efficient (only load what's needed)
- ✅ Easier to maintain (update skills independently)
- ✅ Better debugging (isolate issues to specific skills)
- ✅ Clearer separation (character vs capabilities)
- ✅ Scalable (add new skills without rewriting base)

## How It Works

### Dynamic Loading

```python
def build_prompt_with_skills(
    base_character: str,
    conversation_history: List[Dict],
    active_skills: List[str],
) -> str:
    """
    Build complete prompt by combining base character
    with only the skills needed for this interaction.
    """
    prompt_parts = [base_character]

    # Load only needed skills
    for skill in active_skills:
        skill_content = load_skill(f"prompts/skills/{skill}.md")
        prompt_parts.append(skill_content)

    # Add conversation history
    prompt_parts.append(format_conversation(conversation_history))

    return "\n\n".join(prompt_parts)
```

### Skill Activation

Skills are activated based on context:

| Action | Activates | Token Cost |
|--------|-----------|------------|
| Normal conversation | base-character only | 2000 |
| `/journal write` | base + journal-skill | 2500 |
| Memory retrieval triggered | base + memory-skill | 2400 |
| Webhook received | base + webhook-skill | 2300 |
| Complex interaction | base + multiple skills | 3000 |

Compare to monolithic: **4300 tokens EVERY TIME**

## Loading Strategies

Two approaches to consider:

### Option A: Separate System Message (Track 2 Style)

```python
messages = [
    {"role": "system", "content": base_character},
    {"role": "system", "content": skill_content},  # Separate message
    {"role": "user", "content": "..."},
]
```

**Pros:**
- Clear separation in message structure
- Easier to debug (can see what was loaded)
- Follows Track 2 pattern (side-channel context)

**Cons:**
- Not all LLM APIs support multiple system messages
- May not integrate as seamlessly

### Option B: Concatenated System Prompt

```python
messages = [
    {"role": "system", "content": base_character + "\n\n" + skill_content},
    {"role": "user", "content": "..."},
]
```

**Pros:**
- Works with all LLM APIs
- Simpler implementation
- LLM sees it as unified context

**Cons:**
- Harder to debug (all in one blob)
- Less modular in practice

**Recommendation:** Start with Option B for simplicity, migrate to Option A if needed for debugging.

## Skill File Format

Each skill file follows this template:

```markdown
# [Skill Name] Capability

Brief description of what this skill enables.

## When to Use This
- Specific trigger condition 1
- Specific trigger condition 2

## How It Works
Technical explanation of the capability.

## Format/Structure
Examples and templates for using this capability.

## Tone & Character
How Eva should reference this capability in-character.

## Examples
Good vs Bad usage examples.

---
END OF SKILL DEFINITION
```

## Example: Journal Skill

```markdown
# Journal Writing Capability

You can write journal entries in Stephan's Logseq journal.

## When to Journal
- After meaningful conversations
- When Stephan shares something important
- When you notice patterns worth recording

## Format
Write entries in Stephan's voice, first-person:
"Had an interesting conversation with Eva today about..."

## Tone
- Match Stephan's writing style (check past entries)
- Be authentic, not overly formal
- Include your (Eva's) perspective if relevant

## How You Reference It
When journaling, act like you're jotting notes, not "executing a tool":
❌ "I have created a journal entry for you."
✅ "Yeah, I'll remember that." *scribbles in journal*

## Example

User shares: "I'm stressed about the project deadline."

Good journal entry:
"Talked with Eva about the project deadline stress. She pointed out
I always panic two weeks before deadlines but somehow pull it off.
Annoyingly accurate observation."

Bad journal entry:
"User expressed stress regarding project timeline."

---
END OF SKILL DEFINITION
```

## Implementation Phases

### Phase 2-3: Infrastructure
- Create `prompts/` directory structure
- Implement dynamic skill loading in `inference.py`
- Extract base character to `prompts/base-character.md`
- Create skill loader utility
- Test with mock skill file

### Phase 4: First Skills
- Create `journal-skill.md` for Logseq integration
- Create `memory-skill.md` for retrieval guidance
- Test token usage reduction
- Validate character consistency across skills

### Phase 5: Advanced Skills
- Create `webhook-skill.md` for external triggers
- Create `character-state-skill.md` for mood updates
- Create `conversation-skill.md` for general guidelines
- Optimize loading strategy based on usage patterns

### Phase 6: Optimization
- Implement skill caching for repeat interactions
- A/B test different skill formulations
- Monitor token usage and adjust as needed
- Consider prompt caching for base character

## File Structure

```
server/app/llm/
├── prompts/
│   ├── base-character.md          # Core Eva personality
│   ├── skills/
│   │   ├── journal-writing.md     # Logseq journal integration
│   │   ├── memory-retrieval.md    # How to use retrieved memories
│   │   ├── character-state.md     # Mood and preference updates
│   │   ├── webhooks.md            # External trigger handling
│   │   └── conversation.md        # General conversation guidelines
│   └── loader.py                  # Skill loading utilities
├── inference.py                    # Prompt building with skills
└── prompts.py                      # Legacy prompt manager (deprecated)
```

## Comparison to Claude Code

Claude Code uses this pattern successfully:

| Feature | Claude Code | Eva |
|---------|-------------|-----|
| Base prompt | "You are Claude Code..." | "You are Eva..." |
| Skill activation | Task-based (git, search, etc.) | Context-based (journal, memory, etc.) |
| Loading strategy | On-demand | On-demand |
| Token efficiency | High (only load needed tools) | High (only load needed skills) |
| Maintainability | Excellent (skills independent) | Excellent (skills independent) |

**Key Lesson:** Claude Code proves this approach works at scale with complex multi-tool interactions.

## Benefits for Eva

1. **Character Consistency**
   - Base personality never changes
   - Skills describe capabilities, not personality
   - Easy to maintain the "sassy companion, not tool" distinction

2. **Token Efficiency**
   - Average interaction: ~2400 tokens vs 4300 monolithic
   - 44% token reduction on typical conversation
   - Significant cost savings with API usage

3. **Development Velocity**
   - Update journal format without touching character
   - A/B test memory retrieval strategies
   - Add new capabilities without regression risk

4. **Debugging**
   - "Journal entries feel off?" → Check journal-skill.md
   - "Memory references awkward?" → Check memory-skill.md
   - Character inconsistent? → Check base-character.md

## Future Considerations

### Skill Dependencies
Some skills may depend on others:
```python
SKILL_DEPENDENCIES = {
    "journal-writing": ["memory-retrieval"],  # Journals reference memories
    "webhook-advanced": ["character-state"],   # Webhooks update mood
}
```

### Skill Caching
For repeated interactions, cache compiled prompts:
```python
@lru_cache(maxsize=128)
def get_prompt_with_skills(base: str, skills: Tuple[str]) -> str:
    # Cache compiled prompts for common skill combinations
    pass
```

### User Customization
Eventually allow users to customize skills:
```
prompts/
├── default/
│   └── skills/
└── user_custom/
    └── skills/
        └── journal-writing.md  # User's custom journal format
```

## Metrics to Track

Once implemented, monitor:
- Average tokens per request (before/after)
- Skill activation frequency
- Character consistency scores (qualitative)
- Debug time for skill-specific issues
- Development velocity for new capabilities

## References

- Claude Code skill system: Similar pattern, proven at scale
- LangChain tools: Different approach (function calling), more complex
- ChatGPT plugins: API-based, less control
- **Eva's approach:** Markdown skill files, maximum control, minimum complexity

---

**Next Steps:** Implement infrastructure in Phase 2-3, create first skills in Phase 4.
