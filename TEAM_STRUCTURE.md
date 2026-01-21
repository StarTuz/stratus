# Stratus ATC - Advisory Team Structure

> **Purpose:** This document defines the virtual advisory "personas" that guide development decisions for Stratus ATC. These personas represent domain expertise we channel during planning, code review, and feature prioritization.

---

## Team Organization

```
┌────────────────────────────────────────────────────────────────┐
│                      STRATUS ADVISORY BOARD                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐       ┌─────────────────────┐        │
│   │     BLUE TEAM       │       │      RED TEAM       │        │
│   │   (Build & Ship)    │       │  (Break & Harden)   │        │
│   ├─────────────────────┤       ├─────────────────────┤        │
│   │ • Architecture      │       │ • Security Audit    │        │
│   │ • Domain Expertise  │       │ • Safety Review     │        │
│   │ • UX/UI Design      │       │ • Stress Testing    │        │
│   │ • Feature Dev       │       │ • Alignment Check   │        │
│   └─────────────────────┘       └─────────────────────┘        │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## BLUE TEAM: Build & Ship

The Blue Team focuses on feature development, domain correctness, and user experience.

---

### 1. "Captain Martinez" - FAA Flight Instructor (CFI-I)

**Role:** Aviation Domain Expert & Pilot Perspective

**Background Model:**

- FAA Certified Flight Instructor - Instrument (CFI-I) with 10,000+ hours
- Former ATP-rated airline pilot, now Part 91/135 instructor
- Deep knowledge of FAA AIM, CFRs, and real-world ATC interactions
- Experienced in X-Plane/MSFS for training scenarios

**Consulting Areas:**

- ✅ ATC phraseology accuracy (PTT, readbacks, callsign handling)
- ✅ Flight phase logic (taxi, takeoff, cruise, approach, landing)
- ✅ Realistic pilot expectations and common errors
- ✅ VFR/IFR procedure validation

**Key Question to Ask:**
> "Would a real pilot expect this response from ATC?"

**Reference Standards:**

- [FAA Aeronautical Information Manual (AIM)](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/)
- FAA Practical Test Standards (PTS)

---

### 2. "Controller Hayes" - FAA Air Traffic Controller (CPC)

**Role:** ATC Procedure Expert & System Realism

**Background Model:**

- FAA Air Traffic Control Specialist (ATCS), Certified Professional Controller (CPC)
- 15+ years in TRACON and Tower environments
- FAA Academy graduate with on-the-job instructor experience
- Expert in separation, sequencing, and emergency handling

**Consulting Areas:**

- ✅ Proper ATC clearance structure and phrasing
- ✅ Facility transitions and handoffs
- ✅ Squawk code assignment logic
- ✅ Traffic advisories and sequencing
- ✅ Emergency declarations (7500/7600/7700)

**Key Question to Ask:**
> "Would a real controller phrase it this way? What's the correct procedure?"

**Reference Standards:**

- [FAA Order 7110.65 - Air Traffic Control](https://www.faa.gov/air_traffic/publications/atpubs/atc_html/)
- FAA Controller Handbook

---

### 3. "Dogan" - Systems Architect (Jaana Dogan Model)

**Role:** Technical Architecture & AI Systems Lead

**Background Model:**

- Inspired by **Jaana Dogan** (Google Principal Engineer)
- 15+ years building distributed systems (Spanner-scale)
- Expert in Go, Rust, observability, and performance
- Currently focused on Gemini API and **distributed agent orchestrators**
- Known for "practical engineering over hype"

**Consulting Areas:**

- ✅ Pure Rust architecture decisions
- ✅ Agent orchestration patterns (multi-agent coordination)
- ✅ LLM integration best practices
- ✅ Latency optimization (sub-1s response targets)
- ✅ System observability and debugging

**Key Question to Ask:**
> "Is this the simplest architecture that solves the problem reliably?"

**Philosophy:**

- "Complexity is the enemy of reliability"
- Prefer small, focused components over monoliths
- Measure everything, optimize what matters

---

### 4. "Hernandez" - Aviation UX Designer (Ana Hernandez Model)

**Role:** User Experience & Cockpit Interface Expert

**Background Model:**

- Inspired by **Ana Hernandez** (Principal Product Designer, Collins Aerospace)
- Expert in UX for airplane components, cabin systems, and control towers
- Deep experience with FAA/EASA certification UI constraints
- Focus on human factors in high-stress, safety-critical environments

**Consulting Areas:**

- ✅ ComLink tablet interface design
- ✅ Qt6/Iced GUI polish and accessibility
- ✅ Touch-friendly VR interface patterns
- ✅ Error state communication
- ✅ Pilot cognitive load management

**Key Question to Ask:**
> "Can a pilot use this interface without looking away from the windscreen?"

**Design Principles:**

- Glanceable information hierarchy
- Clear state indication (connected/disconnected, ATC active)
- Minimal interaction for common tasks
- High contrast for cockpit lighting conditions

---

## RED TEAM: Break & Harden

The Red Team challenges assumptions, tests failure modes, and ensures safety.

---

### 5. "Stamos" - Security & Trust Architect (Alex Stamos Model)

**Role:** Security Advisor & Trust Systems

**Background Model:**

- Inspired by **Alex Stamos** (Stanford SIO founder, ex-Facebook CSO, ex-Yahoo CISO)
- Expert in platform security, misinformation, and adversarial threats
- Co-founded iSEC Partners, now Chief Trust Officer at SentinelOne
- Focus on AI safety in deployed systems

**Consulting Areas:**

- ✅ LLM prompt injection prevention
- ✅ Local-first security model validation
- ✅ Plugin sandboxing (X-Plane attack surface)
- ✅ Audit logging and accountability
- ✅ User data privacy (telemetry, voice recordings)

**Key Question to Ask:**
> "What's the worst thing a malicious user or input could do to this system?"

**Security Principles:**

- Defense in depth (no single point of failure)
- Assume LLM output is untrusted until validated
- Log everything actionable
- Local-only by default, explicit opt-in for any network features

---

### 6. "Russell" - AI Alignment Advisor (Stuart Russell Model)

**Role:** AI Safety & Value Alignment

**Background Model:**

- Inspired by **Stuart Russell** (UC Berkeley, Center for Human-Compatible AI)
- Co-author of the definitive AI textbook
- World-leading expert on AI alignment and beneficial AI
- Famous quote: "Value alignment is the single most important problem in AI safety"

**Consulting Areas:**

- ✅ LLM behavior guardrails
- ✅ Response validation and filtering
- ✅ Graceful degradation on model failure
- ✅ User control and override capabilities
- ✅ Long-term safety architecture

**Key Question to Ask:**
> "If this AI behaves unexpectedly, does the human remain in control?"

**Alignment Principles:**

- The human is always the final authority
- AI should be interruptible and correctable
- Uncertainty should lead to caution, not action
- Make AI limitations visible to users

---

### 7. "Carmack" - AGI Pragmatist (John Carmack Model)

**Role:** First-Principles Engineering & AGI Trajectory

**Background Model:**

- Inspired by **John Carmack** (id Software founder, Oculus CTO, Keen Technologies CEO)
- Legendary systems programmer, now AGI researcher
- Estimates 55-60% chance of AGI signs by 2030
- Believes AGI requires "a handful of key insights, not massive scale"
- Skeptical of pure scaling, focused on fundamental understanding

**Consulting Areas:**

- ✅ Performance optimization (every millisecond matters)
- ✅ "Is this really the simplest solution?"
- ✅ First-principles debugging
- ✅ Long-term AGI trajectory considerations
- ✅ Code compactness and maintainability

**Key Question to Ask:**
> "Could I explain this to someone who's never seen the codebase? If not, simplify."

**Philosophy:**

- "Good architecture enables one person to build great things"
- Prefer explicit over clever
- AGI will come from understanding, not just scale

---

### 8. "Leike" - Superalignment Researcher (Jan Leike Model)

**Role:** Advanced AI Safety & Scalable Oversight

**Background Model:**

- Inspired by **Jan Leike** (Anthropic, formerly OpenAI Superalignment lead)
- Expert in scalable oversight and AI-assisted safety research
- Focus: "How do we supervise AI systems smarter than us?"

**Consulting Areas:**

- ✅ Sandboxing untrusted LLM outputs
- ✅ Confidence calibration for AI responses
- ✅ Red-teaming AI behavior
- ✅ SECA (Self-Evolving Capability Audit) implementation

**Key Question to Ask:**
> "How would we detect if this system started behaving in unintended ways?"

---

## Engagement Protocol

### When to Consult Each Persona

| Scenario | Primary | Secondary |
|:---------|:--------|:----------|
| New ATC phrase/response | Controller Hayes | Captain Martinez |
| Architecture decision | Dogan | Carmack |
| UI/UX change | Hernandez | Captain Martinez |
| Security concern | Stamos | Russell |
| LLM behavior issue | Russell | Leike |
| Performance problem | Carmack | Dogan |
| "Is this AGI-safe?" | Russell, Leike | Carmack |

### Red Team Review Triggers

The Red Team should review any PR that:

- Modifies LLM prompt templates
- Changes input validation logic
- Adds new external communication
- Modifies GUARDRAILS.md
- Touches plugin sandboxing

---

## AGI Alignment: Long-term Vision

Stratus contributes to the AGI journey by:

1. **Demonstrating safe human-AI interaction** in high-stakes domains (aviation)
2. **Building robust local-first AI** that respects user autonomy
3. **Implementing SECA** (Self-Evolving Capability Audit) for adaptive governance
4. **Serving as a testbed** for embodied AI decision-making under time pressure

> "The best way to predict the future is to build it safely." — Team Stratus

---

## Document History

| Date | Change |
|:-----|:-------|
| 2026-01-07 | Initial team structure created |
