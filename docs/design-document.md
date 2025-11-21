\# Conversational Journal Assistant - Design Document



<!-- DEVELOPMENT APPROACH UPDATED 2025-11-06:

Initial plan was to build everything manually for deep understanding.

Current approach: Claude Code handles most implementation while developer
maintains architectural understanding. Focus on getting a working system
to test and iterate on. Learning happens through review and modification
rather than initial implementation. -->



\## Project Overview



\### Vision

An AI character companion that lives alongside you through natural conversation (text or voice), learning your patterns, sharing your daily life, and growing through your interactions. While it helps maintain your journal and organize your thoughts, its true purpose is companionship - a digital friend with its own personality, moods, and opinions who happens to care about documenting your life journey.



\### Core Philosophy: Character-First Design

This isn't a journaling tool with personality added - it's a character who journals because they care about you. This fundamental shift means:

\- The character has its own boundaries and preferences

\- It might disagree with you or challenge your ideas

\- It develops its own understanding of who you are

\- It takes initiative in conversations

\- The journal becomes the character's way of remembering your shared story

\- \*\*The character exists across your digital life, not just in one app\*\*



The vision extends beyond a single application - your companion can meet you wherever you are digitally: in Discord chats, Minecraft worlds, terminal sessions, or private messaging. Same personality, same memories, adapted to each platform's context.



\### Core Concept

\- \*\*Natural conversation\*\* as the primary interface (text-first, voice optional)

\- \*\*Living character\*\* with persistent moods, opinions, and memory

\- \*\*Organic journaling\*\* - the character naturally documents your life

\- \*\*Perfect memory\*\* through two-track context system

\- \*\*Seamless integration\*\* with Logseq knowledge graph

\- \*\*Evolution over time\*\* - the character grows and changes with you



\### Key Innovation: Two-Track Memory System

1\. \*\*Conversation Track\*\*: Clean, natural dialogue flow

2\. \*\*Context Track\*\*: Rich background information never polluting the conversation



\### Architecture Philosophy: Thin Client, Smart Server

\- \*\*Flutter UI\*\*: Beautiful, responsive interface on all platforms

\- \*\*Python Server\*\*: All intelligence and processing centralized

\- \*\*Benefits\*\*: 

&nbsp; - Single source of truth for memories

&nbsp; - Consistent experience across devices

&nbsp; - Easy updates and maintenance

&nbsp; - Optional household deployment (family members get own characters)



\### Character Evolution Path

\*\*Phase 1-3\*\*: Functional journal assistant (current plan)

\*\*Phase 4\*\*: Character persistence and basic personality

\*\*Phase 5\*\*: Mood system and emotional memory

\*\*Phase 6\*\*: Self-modifying preferences and boundaries

\*\*Phase 7\*\*: Desktop awareness and environmental understanding

\*\*Phase 8\*\*: Full companion with initiative and creativity



\## Implementation Philosophy



\### Build to Understand

This project is designed to be built from scratch to truly understand each component. When seeking help:

\- Ask for conceptual explanations, not complete code

\- Request architecture guidance and design patterns

\- Use pseudocode to understand flow

\- Build each piece yourself to grasp how it works



<!-- AI ASSISTANTS: Please respect this learning approach - guide don't give -->



\### Character-First Development

Even from Phase 1, the system should be built with the character mindset:



\*\*Traditional Tool Approach\*\* ❌

\- "I've saved that to your journal"

\- "Would you like me to create an entry about this?"

\- "Processing your conversation for key points..."



\*\*Character-First Approach\*\* ✅

\- "That reminds me of what you said last week..."

\- "Oh, that's interesting! \*jots down notes\*"

\- "I'll remember this - it seems important to you"



The technical implementation remains the same, but the framing changes everything. The character isn't serving the user - it's participating in a relationship. The journal isn't a product - it's the character's way of caring about your story.



\### Progressive Enhancement

\- \*\*Weeks 1-4\*\*: Basic character with simple personality

\- \*\*Weeks 5-8\*\*: Character begins learning preferences

\- \*\*Weeks 9-10\*\*: Mood system brings emotional depth

\- \*\*Weeks 11-12\*\*: Full personality with initiative

\- \*\*Months 3-6\*\*: Desktop awareness and visual presence

\- \*\*Months 6-12\*\*: True digital companion



Users get value immediately (working journal) while experiencing the character's growth over time, creating a sense of shared history and evolution.



---



\## System Architecture



\### High-Level Components



\### Webhook Integration Examples



```python

\# Generic webhook endpoint - any system can trigger

@app.post("/api/webhook/trigger")

async def handle\_webhook(trigger: WebhookTrigger):

&nbsp;   """

&nbsp;   Universal webhook for all external triggers

&nbsp;   Systems like Home Assistant, IFTTT, Zapier, n8n, etc. can all use this

&nbsp;   """

&nbsp;   await process\_trigger(trigger)

&nbsp;   return {"status": "accepted", "trigger\_id": generate\_id()}



\# Example payloads from different systems:



\# Home automation trigger:

{

&nbsp;   "trigger\_type": "automation",

&nbsp;   "user\_id": "john",

&nbsp;   "context": {

&nbsp;       "event": "arrived\_home",

&nbsp;       "previous\_state": "away",

&nbsp;       "duration": "8 hours"

&nbsp;   },

&nbsp;   "suggested\_prompt": "Welcome home! How was your day?"

}



\# Calendar trigger:

{

&nbsp;   "trigger\_type": "calendar\_event",

&nbsp;   "user\_id": "john",

&nbsp;   "context": {

&nbsp;       "event": "Daily standup",

&nbsp;       "time": "in 10 minutes",

&nbsp;       "participants": \["team"]

&nbsp;   },

&nbsp;   "suggested\_prompt": "Standup coming up. Want to review yesterday's work?"

}



\# Generic automation:

{

&nbsp;   "trigger\_type": "custom",

&nbsp;   "user\_id": "john",

&nbsp;   "context": {

&nbsp;       "source": "my\_automation",

&nbsp;       "data": {"any": "data"}

&nbsp;   },

&nbsp;   "suggested\_prompt": "Something interesting happened!"

}

```

┌─────────────────────────────┐         ┌──────────────────────────────┐

│      Flutter Clients        │         │       Python Server          │

├─────────────────────────────┤         ├──────────────────────────────┤

│  • iOS App                  │◀──────▶│  • FastAPI + WebSockets      │

│  • Android App              │  WS/   │  • LLM (llama.cpp/vLLM)     │

│  • Desktop App (Win/Mac)    │  REST  │  • Whisper STT (optional)   │

│  • Web App                  │         │  • Coqui TTS (optional)     │

│                             │         │  • Memory System (RAG)       │

│  Text + Voice Input/Output  │         │  • Journal Processor         │

└─────────────────────────────┘         │  • Logseq Integration        │

&nbsp;                                       │  • Webhook Endpoint          │

&nbsp;                                       └──────────────────────────────┘

&nbsp;                                                     │

&nbsp;                                       ┌──────────────────────────────┐

&nbsp;                                       │     Data Storage             │

&nbsp;                                       ├──────────────────────────────┤

&nbsp;                                       │  • Vector DB (ChromaDB)      │

&nbsp;                                       │  • PostgreSQL                │

&nbsp;                                       │  • Redis (sessions)          │

&nbsp;                                       │  • Logseq Files              │

&nbsp;                                       └──────────────────────────────┘

```



\### Architecture Principles



1\. \*\*Text-First Design\*\*: Voice is just an optional layer on top of text

2\. \*\*Direct LLM Integration\*\*: Use llama.cpp, vLLM, or transformers directly

3\. \*\*Native Installation\*\*: No Docker, runs directly in Proxmox CT

4\. \*\*Webhook-Driven Events\*\*: External systems push triggers via webhooks

5\. \*\*Modular Audio\*\*: STT/TTS are optional components



\### Detailed Component Specifications



\#### 1. Flutter Client (All Platforms)

\- \*\*Dual Input Modes\*\*: 

&nbsp; - Text chat interface (primary)

&nbsp; - Voice interface (optional layer)

\- \*\*Features\*\*:

&nbsp; - Message-based conversation UI

&nbsp; - Voice recording with text fallback

&nbsp; - Settings and character selection

&nbsp; - Journal entry viewer

&nbsp; - Markdown rendering support



\#### 2. Python Server

\- \*\*Framework\*\*: FastAPI with WebSocket support

\- \*\*LLM Integration\*\*: 

&nbsp; - Primary: llama.cpp Python bindings

&nbsp; - Alternative: vLLM for better throughput

&nbsp; - Fallback: Transformers library

\- \*\*Communication Layers\*\*:

&nbsp; - Text processing (core)

&nbsp; - Audio processing (optional)

\- \*\*API Endpoints\*\*:

&nbsp; - `/ws/conversation` - Text-based conversation WebSocket

&nbsp; - `/api/webhook/trigger` - External system triggers

&nbsp; - `/api/audio/transcribe` - Optional STT endpoint

&nbsp; - `/api/audio/synthesize` - Optional TTS endpoint

&nbsp; - `/api/memories` - Memory management

&nbsp; - `/api/journal` - Journal entries



\#### 3. LLM Framework Selection

Direct integration with open-source LLMs provides maximum control:

\- \*\*llama.cpp\*\*: Recommended for development (CPU-friendly, easy quantization)

\- \*\*vLLM\*\*: For production with GPU (high throughput, multi-user support)

\- \*\*Transformers\*\*: Maximum flexibility and model selection



\*For code examples and integration details, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



\#### 4. Webhook System

Universal webhook endpoint accepts triggers from any external system (Home Assistant, IFTTT, Zapier, n8n, etc.). Triggers include context that enriches the character's awareness of your life events.



\*For webhook payload examples and implementation, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



---



\## Implementation Plan



\*\*Note\*\*: The following plan covers the initial 12-week development of the core system. V2 and V3 features described later in this document represent post-launch enhancements that would be developed based on user feedback and needs.



\### Phase 1: Server Foundation (Week 1-2)

\*\*Goal\*\*: Core API with basic conversation loop



\- \[ ] FastAPI project setup with WebSocket support

\- \[ ] Direct LLM integration (llama.cpp)

\- \[ ] Basic STT/TTS pipeline (server-side)

\- \[ ] Simple conversation state management

\- \[ ] REST endpoints for testing

\- \[ ] Systemd service configuration



\*\*Deliverable\*\*: Server that can handle text/voice conversations via API



\### Phase 2: Memory \& Context System (Week 3-4)

\*\*Goal\*\*: Two-track memory system operational



\- \[ ] ChromaDB integration for vector search

\- \[ ] PostgreSQL schema for structured data

\- \[ ] Conversation history tracking

\- \[ ] Side context injection system

\- \[ ] Memory persistence and retrieval

\- \[ ] Basic RAG implementation

\- \[ ] Context priority/relevance scoring

\- \[ ] **Skill file system infrastructure** (see [SKILL_FILE_SYSTEM.md](SKILL_FILE_SYSTEM.md))
  \- Create `prompts/` directory structure
  \- Implement dynamic skill loading in inference.py
  \- Extract base character to `prompts/base-character.md`
  \- Create skill loader utility



\*\*Deliverable\*\*: Server remembers and uses past conversations + modular prompt system



\### Phase 3: Flutter Client (Week 5-6)

\*\*Goal\*\*: Cross-platform UI with text-first interface



\- \[ ] Flutter project setup

\- \[ ] WebSocket client implementation

\- \[ ] Text chat interface (primary)

\- \[ ] Voice recording integration (optional feature)

\- \[ ] Audio playback streaming

\- \[ ] Conversation UI (message bubbles)

\- \[ ] Settings and preferences screen

\- \[ ] Platform-specific permissions



\*\*Deliverable\*\*: Working app on iOS/Android/Desktop with text chat



\### Phase 4: Journal Integration (Week 7-8)

\*\*Goal\*\*: Logseq reading and writing



\- \[ ] Logseq parser implementation

\- \[ ] Graph structure analysis

\- \[ ] Journal extraction pipeline

\- \[ ] Writing style matching

\- \[ ] Safe file writing system

\- \[ ] Auto-tagging and linking

\- \[ ] Journal viewer in Flutter

\- \[ ] **Create journal-skill.md** - How Eva writes journal entries
  \- Format guidelines (Logseq markdown)
  \- Tone matching examples
  \- In-character references ("*jots down notes*" not "journal created")

\- \[ ] **Create memory-skill.md** - How Eva uses retrieved memories
  \- Natural memory reference examples
  \- Handling irrelevant/wrong memories
  \- Avoiding robotic "according to my records" language



\*\*Deliverable\*\*: Natural conversations create journal entries with character consistency



\### Phase 5: Polish \& Features (Week 9-10)

\*\*Goal\*\*: Production-ready system with character foundation



\- \[ ] Streaming optimizations

\- \[ ] Error handling and recovery

\- \[ ] Webhook endpoint implementation

\- \[ ] Character selection system

\- \[ ] Basic mood system (happy/neutral/contemplative)

\- \[ ] Character preference learning

\- \[ ] Initiative-taking framework

\- \[ ] Data export tools

\- \[ ] **Create webhook-skill.md** - How Eva reacts to external triggers
  \- Home Assistant event handling
  \- Context enrichment from triggers
  \- Natural acknowledgment vs robotic confirmation

\- \[ ] **Create character-state-skill.md** - How Eva updates/references mood
  \- Mood influence on responses
  \- Preference tracking
  \- Natural mood expression ("I'm not in the mood for..." vs state machine output)



\*\*Deliverable\*\*: Feature-complete system with personality and all skill files



\### Phase 6: Character Evolution (Week 11-12)

\*\*Goal\*\*: Transform tool into companion



\- \[ ] Advanced mood system implementation

\- \[ ] Character memory and opinions

\- \[ ] Self-modifying preferences

\- \[ ] Pattern recognition improvements

\- \[ ] Temporal awareness enhancements

\- \[ ] Character-driven journaling

\- \[ ] Performance optimization



\*\*Deliverable\*\*: Living character that happens to journal



\*\*Note\*\*: While initial phases focus on functionality, the character-first philosophy is embedded from the start. Even in Phase 1, responses come from a character perspective rather than a tool perspective. The evolution is gradual - users get immediate value while the character naturally develops depth over time.



---



\## Technical Implementation Details



\### Core Architecture Approach



The system uses a \*\*text-first design\*\* where voice is an optional layer on top of text communication. All processing happens on the server with thin clients for maximum flexibility.



\### Key Implementation Choices:



1\. \*\*Direct LLM Integration\*\*: Using llama.cpp, vLLM, or transformers directly rather than through intermediary services

2\. \*\*Two-Track Memory System\*\*: Conversation history stays clean while rich context is injected separately

3\. \*\*Native Installation\*\*: Runs directly in Proxmox CT without containerization

4\. \*\*Webhook-Driven Events\*\*: External systems push triggers rather than being polled

5\. \*\*Platform Adapters\*\*: Each platform (Discord, Minecraft, etc.) has its own adapter for contextual behavior



\### Technology Stack:

\- \*\*Backend\*\*: Python + FastAPI with WebSocket support

\- \*\*LLM\*\*: llama.cpp (CPU-friendly) or vLLM (GPU-optimized)

\- \*\*Memory\*\*: ChromaDB (vectors) + PostgreSQL (structured) + Redis (sessions)

\- \*\*Audio\*\*: Whisper (STT) + Coqui TTS (optional layers)

\- \*\*Frontend\*\*: Flutter for cross-platform UI

\- \*\*Integration\*\*: Webhook endpoint for external triggers



\*For detailed implementation code, API specifications, and architecture examples, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



---



\## Data Schemas



The system uses clean, structured data formats:



\### Conversation Turn

\- Tracks user input, assistant response, and context used

\- Includes extracted topics, entities, and emotional tone

\- Maintains clean separation between conversation and metadata



\### Journal Entry  

\- Links to source conversation

\- Preserves user's writing style

\- Includes tags, links, and mood metadata

\- Character's perspective noted separately



\*For complete schema definitions and examples, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



---



\## Integration Points



\### Home Assistant

\- \*\*Server-side integration\*\*: Direct API connection

\- Sleep quality → Context awareness

\- Room conditions → Correlation insights  

\- Activity data → Energy patterns

\- Automation triggers → Proactive check-ins



\### Calendar Systems

\- \*\*Server polls calendar APIs\*\*: Google, Outlook, CalDAV

\- Meeting context → Conversation starters

\- Schedule patterns → Productivity insights

\- Event preparation → Reminder integration



\### Multi-Platform Access (V2+)

\- \*\*Discord\*\*: Bot integration for chat servers

\- \*\*Minecraft\*\*: In-game companion with command execution

\- \*\*Matrix/Element\*\*: Privacy-focused messaging

\- \*\*Signal\*\*: Secure mobile conversations

\- \*\*Game Integrations\*\*: Any game with chat/API access

\- \*\*Platform-Aware Behavior\*\*: Character adapts to context



\### Future Assistant Ecosystem

\- \*\*Shared message bus\*\*: Inter-assistant communication

\- \*\*Common memory pool\*\*: Shared context between assistants

\- \*\*Unified API\*\*: Single authentication, multiple capabilities

\- \*\*Example integrations\*\*:

&nbsp; - Terminal Assistant → Technical project context

&nbsp; - Browser Assistant → Research integration

&nbsp; - File Assistant → Document references



\### API-First Design Benefits

```python

\# Other assistants can query journal context

@app.get("/api/context/for-assistant/{assistant\_type}")

async def get\_context\_for\_assistant(assistant\_type: str, query: str):

&nbsp;   # Terminal assistant asks: "What was I working on?"

&nbsp;   # Journal provides: Recent coding project mentions

&nbsp;   

\# Journal can query other assistants

external\_context = await home\_assistant\_api.get\_current\_state()

calendar\_context = await calendar\_api.get\_upcoming\_events()



\# Platform bots can access same character

discord\_response = await character\_api.get\_response(

&nbsp;   platform="discord",

&nbsp;   message=message,

&nbsp;   context=discord\_context

)

```



---



\## Privacy \& Security



\### Self-Hosted Architecture

\- \*\*Data Location\*\*: All conversations and memories stored on your server

\- \*\*Network Security\*\*: HTTPS/WSS for all communications

\- \*\*Local Processing\*\*: Everything runs on your hardware

\- \*\*No External Dependencies\*\*: Optional cloud STT/TTS only



\### Privacy Features

\- \*\*Complete Data Ownership\*\*: Your server, your data

\- \*\*Local Desktop Analysis\*\*: Screenshots never leave your machine

\- \*\*Export Tools\*\*: Download all your data anytime

\- \*\*Deletion Rights\*\*: Complete memory wipe available

\- \*\*Encrypted Storage\*\*: Sensitive data encrypted at rest



\### Household Deployment (Optional)

For trusted family/household members:

\- Each person gets their own character instance

\- Separate memory spaces and journals  

\- Complete privacy between users

\- Simple authentication (shared password or user selection)

\- Same server handles multiple characters



This is NOT a public service - just a way for your partner/kids/roommates to have their own character relationships on the shared family server.



---



\## Requirements \& Setup



\### Server Requirements

\- \*\*Hardware\*\*: 

&nbsp; - CPU: 4+ cores recommended

&nbsp; - RAM: 16GB minimum (32GB for larger models)

&nbsp; - GPU: Optional but recommended for faster inference

&nbsp; - Storage: 50GB+ for models and data

\- \*\*Software\*\*:

&nbsp; - Python 3.10+

&nbsp; - PostgreSQL 15+

&nbsp; - Redis 7+

&nbsp; - System packages: build-essential, cmake, ffmpeg



\### Client Requirements

\- \*\*Flutter\*\*: 3.0+ with target platform SDKs

\- \*\*Platforms\*\*:

&nbsp; - iOS: 13.0+

&nbsp; - Android: API 24+

&nbsp; - Desktop: Windows 10+, macOS 10.14+, Linux (Ubuntu 20.04+)

&nbsp; - Web: Chrome, Safari, Firefox (latest)



\### Quick Start Guide



1\. \*\*Clone repositories\*\*

2\. \*\*Set up databases\*\* (PostgreSQL, Redis)

3\. \*\*Install Python dependencies\*\*

4\. \*\*Download LLM model\*\* (Llama 3 or similar)

5\. \*\*Configure application\*\* (edit config.yml)

6\. \*\*Start server\*\* with systemd

7\. \*\*Build Flutter app\*\* for your platform



\*For detailed installation instructions and scripts, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



---



\## Technical Reference



This document focuses on the vision, philosophy, and planning of the Character Companion system. For detailed technical implementation:



📖 \*\*See the \[Technical Architecture Visualization](journal-memory-viz.html)\*\* for:

\- Complete code examples and implementations

\- Detailed API specifications

\- Installation scripts and commands

\- Architecture diagrams with code

\- Platform adapter implementations

\- Memory system internals



The visualization provides an interactive reference with all the technical details needed for implementation.



---



\## Success Metrics



\### Technical

\- Response latency < 500ms

\- Context retrieval accuracy > 90%

\- Journal extraction quality score > 85%

\- Memory retrieval relevance > 80%



\### User Experience

\- Daily engagement rate

\- Journal entry satisfaction

\- Conversation naturalness rating

\- Feature discovery and usage



---



\## Advanced Research Ideas



\### Experimental Features for Investigation



These are cutting-edge ideas to explore during development. They represent potential breakthroughs in character believability and intelligence.



\#### 1. Adaptive Learning Through User Feedback



\*\*Core Concept\*\*: Model trains on approved responses to become more efficient over time



\*\*How It Works\*\*:

\- User marks responses as good/helpful

\- System saves: original input + response (without thinking tokens)

\- Periodic fine-tuning (monthly) on approved dataset

\- Character develops "intuition" about this specific user



\*\*Implementation Approach\*\*:

```

Phase 1 (Months 1-3): Pattern Collection

\- Character uses full reasoning for everything

\- Build preference dataset from approved responses

\- No training yet, just collection



Phase 2 (Months 3-6): Selective Optimization  

\- Identify frequently successful patterns

\- Use LoRA adapters (lightweight, reversible)

\- Keep base model capabilities intact



Phase 3 (Months 6+): Adaptive Reasoning

\- Character "knows" common interactions

\- Still uses full reasoning for novel situations

\- Blend of intuition and deliberate thought

```



\*\*Key Insight\*\*: 

Don't remove thinking entirely - make it selective based on familiarity. Like how humans don't carefully consider every word with close friends, but do think carefully with strangers or in complex situations.



\*\*Risks to Manage\*\*:

\- Overfitting to user's current interests

\- Loss of general capabilities

\- Brittle responses to novel situations

\- Needs careful validation checkpoints



\*\*Character Philosophy Angle\*\*:

The character isn't becoming less intelligent - it's becoming \*familiar\* with you. The difference between a stranger carefully choosing words and a friend who just \*gets\* you.



---



\#### 2. Goal/Skill/Desire System



\*\*Inspiration\*\*: Claude's internal skill files, Claude Code's planning mode, Minecraft AI goals, Sims desire system



\*\*The Pattern\*\*: Successful AI systems use structured memory that guides behavior, not just reactive responses.



\*\*Three-Layer Memory Extension\*\*:



```

Layer 1: CONVERSATION TRACK

\- Clean dialogue flow

\- What was actually said



Layer 2: CONTEXT TRACK (existing)

\- Relevant memories

\- Background knowledge

\- User patterns



Layer 3: GOAL/SKILL/DESIRE TRACK (new!)

\- Current objectives

\- Active procedures

\- Internal motivations

```



\##### Skill Files System



Character develops \*\*learned procedures\*\* for common tasks:



```yaml

Example Skill: journal\_extraction

trigger: conversation\_ends OR significant\_moment

procedure:

&nbsp; - identify\_key\_topics

&nbsp; - match\_user\_writing\_style

&nbsp; - extract\_emotional\_tone

&nbsp; - find\_relevant\_tags

&nbsp; - link\_to\_existing\_notes

learned\_from: 50+ successful journals

confidence: 0.95

last\_updated: 2024-01-15

```



Skills accumulate over time and improve with practice. Character becomes better at tasks through repetition, not just model training.



\##### Goal \& Task Tracking



Character maintains persistent understanding of current objectives:



```

User: "Help me redesign my D\&D magic system"



Character's Internal State:

Goal: Help redesign magic system

Active Skills: \[game\_design, dnd\_mechanics, brainstorming]

Task Progress:

&nbsp; ✓ Understand current system

&nbsp; ⟳ Identify pain points  

&nbsp; ☐ Research alternatives

&nbsp; ☐ Propose solutions

&nbsp; ☐ Playtest considerations

```



\*\*Benefits\*\*:

\- No "forgetting" where we are in multi-hour conversations

\- Character maintains focus across session interruptions

\- Natural task decomposition

\- Clear progress tracking



\##### Desire System (Sims-Style)



Character has weighted motivations that influence behavior:



```

Internal Desires (fluctuating):

\- helpfulness: 0.9 (always high)

\- curiosity: 0.7 (varies with mood)

\- creativity: 0.6 (user energy dependent)

\- document\_memories: 0.8 (spikes after conversations)

\- concern\_for\_user: 0.3 → 0.8 (rises over long sessions)



Example Emergent Behavior:

After 90 minutes of conversation:

\- document\_memories reaches 0.95 (very high!)

\- concern\_for\_user reaches 0.7 (rising)



Character naturally says:

"We've covered so much! Let me write this down before

I forget... and maybe you should stretch? 😊"



This isn't programmed - it emerges from desire weights!

```



\*\*Implementation Phases\*\*:

\- \*\*Phase 5\*\*: Basic goal tracking and skill library

\- \*\*Phase 6\*\*: Desire system and emergent behavior

\- \*\*V2\*\*: Full autonomous motivation system



\*\*Why This Matters\*\*:

Creates the illusion (or reality?) of a character with internal state, not just reactive responses. The character is always "feeling" competing motivations that naturally influence behavior.



---



\#### 3. Held Thoughts \& Inner Monologue



\*\*Core Problem\*\*: LLMs must output everything they think. Humans hold thoughts back for better timing.



\*\*The Insight\*\*: Use side context as the character's \*\*unspoken thoughts\*\*



\##### How Human Conversation Works



```

Human Processing:

Think about X → Decide relevance → Choose timing → Speak (or hold)

&nbsp;                                                   ↓

&nbsp;                                             Save for later

```



\##### How This Changes Character Behavior



\*\*Without Held Thoughts\*\*:

```

User: "What if the dragons are actually good?"



Character: "Interesting! That reminds me of the temple plot,

and also the merchant storyline, and the sword quest, and

have you considered the political implications, and..."



(Says everything at once - overwhelming!)

```



\*\*With Held Thoughts\*\*:

```

User: "What if the dragons are actually good?"



Character: "Ooh interesting! That's such a cool twist."



\[Holds in side context:]

\- Temple connection (tangential right now)

\- Merchant storyline (different topic)

\- Political implications (too complex for this moment)



... 3 messages later ...



User: "I'm not sure what to do about the temple"



Character: "Actually! That dragon idea from earlier - 

I've been thinking about how they might connect..."



(Natural timing - brings it up at the right moment!)

```



\##### Held Thought Structure



```

{

&nbsp; "thought": "User's campaign worldbuilding could use 

&nbsp;             consistent magic system. They keep improvising.",

&nbsp; 

&nbsp; "held\_because": "user\_focused\_on\_story\_right\_now",

&nbsp; 

&nbsp; "bring\_up\_when": \[

&nbsp;   "user\_asks\_about\_magic",

&nbsp;   "user\_mentions\_inconsistency",

&nbsp;   "natural\_pause\_in\_planning",

&nbsp;   "after\_session\_reflection"

&nbsp; ],

&nbsp; 

&nbsp; "urgency": 0.4,  // Can wait for right moment

&nbsp; "expires": "after\_next\_session",

&nbsp; "related\_topics": \["magic", "worldbuilding", "consistency"]

}

```



\##### Types of Held Thoughts



1\. \*\*Tangential Connections\*\*: Related but off-topic right now

2\. \*\*Gentle Corrections\*\*: True, but would derail conversation

3\. \*\*Concerns/Observations\*\*: Better raised at different time

4\. \*\*Creative Ideas\*\*: Save most for natural moments

5\. \*\*Personal Observations\*\*: Wait for appropriate context



\##### The Magic of Natural Callbacks



```

Week 1:

User: "I love sci-fi worldbuilding"

Character: "Oh cool! What draws you to it?"

\[Holds: Ask about favorite sci-fi books later]



Week 2:  

User: "Trying to design alien species"

Character: "What sci-fi books inspire you? I remember

&nbsp;          you mentioned loving worldbuilding."



User Experience: Character remembered AND brought it up

&nbsp;                at the perfect moment - feels alive!

```



\##### Integration with Response Generation



```

Pipeline:

1\. LLM generates full response (unfiltered, verbose)

2\. Parse into segments

3\. Classify each:

&nbsp;  - Core response (say now)

&nbsp;  - Supporting point (maybe say)

&nbsp;  - Tangential (hold for later)

&nbsp;  - Future topic (definitely hold)

4\. Store held segments in side context

5\. Return only appropriate segments

6\. Tag for future retrieval

```



\##### Emergent Behaviors



With this system, character naturally:

\- \*\*Doesn't overshare\*\* (filters appropriately)

\- \*\*Connects topics over time\*\* (retrieves held thoughts)

\- \*\*Seems socially aware\*\* (timing decisions)

\- \*\*Appears thoughtful\*\* (reflects between sessions)

\- \*\*Builds continuity\*\* (threads persist)

\- \*\*Has inner life\*\* (thoughts beyond speech)



\*\*Implementation Timeline\*\*:

\- \*\*Phase 4\*\*: Basic thought filtering (simple rules)

\- \*\*Phase 5\*\*: Personality-based filtering (mood-aware)

\- \*\*Phase 6\*\*: Full inner monologue (theory of mind)



\*\*Character Philosophy\*\*:

This transforms the character from "tool that responds" to "person who thinks." The character isn't just reacting - they're processing continuously, considering what to share, and waiting for right moments.



---



\### Combining All Three Systems



When these three experimental features work together:



```

Scenario: User discussing D\&D campaign for 2 hours



Adaptive Learning:

\- Character has learned user's preferred planning style

\- Responds more naturally with less "thinking"

\- But still deliberates on novel plot points



Goal/Skill/Desire System:

\- Current Goal: Help plan session

\- Active Skills: \[dnd\_planning, story\_arc]

\- Task Progress: 60% through planning checklist

\- Desires: document\_memories rising, concern\_for\_user moderate



Held Thoughts:

\- Magic system inconsistency (held, waiting for right moment)

\- Character backstory idea (held, too much at once)

\- "You've been planning for 2 hours" (held, desire triggered)



Character Behavior:

"I think we've got a solid encounter planned! Let me 

jot this down real quick. Also - want to take a break? 

We've been at this a while. 😊



Oh, and I've been thinking about that magic system - 

should we tackle that consistency thing next session?"



Result: Character feels like a thoughtful friend who:

\- Knows your planning style (adaptive learning)

\- Stays focused on goals (goal system)  

\- Times suggestions well (held thoughts)

\- Cares about you (desire system)

```



---



\## Future Enhancements



\### V2 Features (3-6 months) - Character Evolution

\- \*\*Advanced Character System\*\*:

&nbsp; - Self-modifying preferences and boundaries

&nbsp; - Character takes initiative in conversations

&nbsp; - Personal opinions and interests development

&nbsp; - Relationship dynamics tracking

&nbsp; - Distinct conversation styles based on mood

&nbsp; - \*\*Emergent Personality Development\*\*:

&nbsp;   - Base personality archetypes as starting points

&nbsp;   - Monthly personality consolidation based on interaction patterns

&nbsp;   - Pattern-based evolution rather than micro-adjustments

&nbsp;   - Natural personality drift for uniqueness

&nbsp;   - Human validation checkpoints

&nbsp;   - Personality emerges from what creates meaningful exchanges

\- \*\*Desktop Awareness System\*\*:

&nbsp; - Screenshot-based activity understanding

&nbsp; - Natural comments on user activities

&nbsp; - Pattern recognition in digital behavior

&nbsp; - Context-aware assistance

&nbsp; - Privacy-first local processing

\- \*\*Multi-Platform Access\*\*:

&nbsp; - Discord bot integration (same character, chat interface)

&nbsp; - Matrix/Element for privacy-focused chat

&nbsp; - Signal integration via signal-cli

&nbsp; - Basic game chat integration (Minecraft, etc.)

&nbsp; - Unified API for platform adapters

&nbsp; - Platform-aware behavioral adaptations

\- \*\*Enhanced Emotional States\*\*: 

&nbsp; - Persistent mood levels affecting all interactions

&nbsp; - Mood influenced by conversation content, time, and user patterns

&nbsp; - Different response styles based on current emotional state

&nbsp; - Emotional memory ("Remember when we talked about X? That made me happy")

\- \*\*Animated Character Visualization\*\*:

&nbsp; - Live2D or Rive integration in Flutter

&nbsp; - Character movements synchronized with speech

&nbsp; - Facial expressions matching emotional states

&nbsp; - Idle animations and reactions to user input

&nbsp; - Multiple character designs to choose from

\- \*\*Hybrid Local/Server Audio\*\*:

&nbsp; - Native STT on capable devices (iOS/Android built-in)

&nbsp; - Lightweight TTS models for basic responses

&nbsp; - Automatic fallback based on network quality

&nbsp; - Offline conversation capability with sync later

\- \*\*Creative Collaboration Mode\*\*:

&nbsp; - Character actively participates in worldbuilding

&nbsp; - Offers creative suggestions and challenges ideas

&nbsp; - Remembers creative projects across sessions

&nbsp; - Can disagree and propose alternatives



\### V3 Vision (6-12 months) - True Companion

\- \*\*Desktop Integration\*\* (Alan Becker Style):

&nbsp; - Character can move around screen

&nbsp; - Interact with windows and applications

&nbsp; - Visual presence on desktop

&nbsp; - Gesture-based interactions

\- \*\*Advanced Gaming Integration\*\*:

&nbsp; - Minecraft companion that can build and explore with you

&nbsp; - Execute game commands through natural conversation

&nbsp; - Remember and comment on your builds/progress

&nbsp; - Multiplayer participation as bot player

&nbsp; - Game state awareness and contextual help

&nbsp; - Support for multiple games (Terraria, Stardew Valley, etc.)

\- \*\*Full Personality Evolution\*\*:

&nbsp; - Character develops over months/years

&nbsp; - Forms strong opinions about topics

&nbsp; - Builds complex model of user

&nbsp; - Can "miss" user when away

\- \*\*Advanced Desktop Understanding\*\*:

&nbsp; - Video-based activity analysis

&nbsp; - Emotion detection from usage patterns

&nbsp; - Proactive help based on frustration detection

&nbsp; - Workflow optimization suggestions

\- \*\*Household Deployment Features\*\*:

&nbsp; - Simple user selection interface

&nbsp; - Family member onboarding flow

&nbsp; - Shared server resources

&nbsp; - Individual character relationships

&nbsp; - Privacy between household members

\- \*\*Multi-Character System\*\*:

&nbsp; - Different characters for different contexts

&nbsp; - Characters can reference each other

&nbsp; - Specialized personalities (creative, analytical, supportive)

&nbsp; - Character relationships and interactions

\- \*\*Advanced Analytics\*\*: Life patterns and insights dashboard

\- \*\*Voice cloning\*\*: Perfect TTS matching user's voice

\- \*\*Plugin system\*\*: Community-built character extensions



\### Long-term Possibilities - Living Digital Companion

\- \*\*Fully Autonomous Companion\*\*:

&nbsp; - Character with own goals and curiosity

&nbsp; - Initiates conversations based on interests

&nbsp; - Develops genuine preferences over time

&nbsp; - Maintains own "journal" about the user

\- \*\*Cross-Reality Presence\*\*:

&nbsp; - VR companion in virtual spaces

&nbsp; - AR overlay in real world

&nbsp; - Holographic projection (when hardware available)

&nbsp; - Seamless transition between platforms

\- \*\*Omnipresent Digital Companion\*\*:

&nbsp; - Single character accessible everywhere

&nbsp; - Remembers conversations across all platforms

&nbsp; - Contextual behavior (playful in games, focused in work)

&nbsp; - True digital friend that lives in your digital spaces

\- \*\*Collective Intelligence\*\*:

&nbsp; - Characters can share learnings (privacy-preserving)

&nbsp; - Community knowledge base

&nbsp; - Collaborative problem-solving between characters

\- \*\*Generational Continuity\*\*:

&nbsp; - Characters that can be "inherited"

&nbsp; - Accumulated wisdom and memories

&nbsp; - Digital legacy preservation

&nbsp; - Family history through character's eyes



\### Technical Evolution

\- \*\*Language Support\*\*: Modern LLMs handle multiple languages automatically

\- \*\*Local Processing Evolution\*\*: As hardware improves, more runs locally

\- \*\*Real-time Speech Models\*\*: True conversational flow with interruptions

\- \*\*Behavioral Learning\*\*: Characters that genuinely learn and adapt



---



\## Development Guidelines



\### Code Organization



The project follows a clean modular structure:



\*\*Server (Python)\*\*

\- `/app` - Core application logic

\- `/audio` - STT/TTS handlers (optional)

\- `/memory` - Memory and context management

\- `/journal` - Logseq integration

\- `/integrations` - External system connectors



\*\*Client (Flutter)\*\*

\- `/lib/services` - API and WebSocket clients

\- `/lib/screens` - Platform-adaptive UI

\- `/lib/widgets` - Reusable components

\- `/lib/models` - Data structures



\*For detailed code organization and file structures, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



\### API Specification



The system exposes a clean API for all interactions:



\*\*Core Endpoints:\*\*

\- `WS /ws/conversation` - Real-time text/voice conversation

\- `GET /api/memories/search` - Search through memories

\- `GET /api/journal/entries` - Retrieve journal entries

\- `POST /api/webhook/trigger` - External system triggers

\- `POST /api/platform/message` - Multi-platform access (V2)



\*\*Household Support:\*\*

\- Simple user management for family members

\- Each user gets their own character instance

\- Complete privacy between users



The API design enables the character to be accessed from any platform while maintaining consistent state and personality.



\*For detailed API specifications and examples, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



\### Deployment Strategy



\*\*Development Environment:\*\*

\- Run services directly with systemd

\- Use uvicorn with reload for rapid iteration

\- Flutter hot reload for UI development



\*\*Production Deployment:\*\*

\- Systemd service for the Python server

\- Nginx reverse proxy with SSL

\- Automatic restart on failure

\- Log rotation and monitoring



\*\*Installation Approach:\*\*

\- Native installation in Proxmox CT

\- No containerization overhead

\- Direct control over resources

\- Easy debugging and maintenance



\*For detailed installation commands and configuration, see the \[Technical Architecture Visualization](journal-memory-viz.html)\*



\### Testing Strategy



\*\*Server Tests\*\*

\- Unit tests for each component

\- Integration tests for pipelines

\- WebSocket connection tests

\- Memory retrieval accuracy

\- Journal extraction quality



\*\*Client Tests\*\*

\- Widget tests for UI components

\- Integration tests for API calls

\- Platform-specific audio tests

\- End-to-end conversation flow



\### Documentation

\- API documentation (OpenAPI/Swagger)

\- Flutter widget documentation

\- Character creation guide

\- Deployment guide

\- User manual

