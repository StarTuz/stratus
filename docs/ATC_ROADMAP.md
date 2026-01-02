# Stratus Offline ATC - Development Roadmap

## Current Status: Phase 2 Complete ✅

Phase 2 is operational. ATC now identifies itself by airport name (e.g., "Truckee Tower") using a local database lookup.

---

## Phase 1: Foundation ✅ (Complete)

**Goal**: Basic Listen → Think → Speak pipeline

- [x] D-Bus integration with speechserverdaemon
- [x] PTT → STT → LLM → TTS flow
- [x] Basic ATC phraseology prompts
- [x] Telemetry injection (position, altitude, frequency)
- [x] Conversation history (10 exchanges)
- [x] Visual comms history in UI

---

## Phase 2: Airport Awareness ✅ (Complete)

**Goal**: ATC knows which airport/facility it is

- [x] Integrated OurAirports database (12MB CSV)
- [x] Logic to lookup nearest airport from coordinates
- [x] Dynamic facility identification in ATC prompts
- [x] Updated phraseology examples with specific facility names

---

## Phase 3: Realistic Ground Operations

**Goal**: Proper taxi, takeoff, and landing sequences

| Task | Difficulty | Impact |
|------|------------|--------|
| Track flight phase (parked → taxi → takeoff → cruise → approach → landing) | Medium | High |
| Proper taxi clearance with hold short | Medium | High |
| ATIS simulation (from METAR data) | Medium | Medium |
| Runway assignment based on wind | Medium | Medium |
| Departure frequency handoff | Easy | Medium |

**Result**: Full ground-to-takeoff sequence with proper clearances

---

## Phase 4: VFR Flight Following

**Goal**: Realistic en-route VFR services

| Task | Difficulty | Impact |
|------|------------|--------|
| Squawk code assignment (unique per flight) | Easy | High |
| "Radar contact" with position confirmation | Easy | High |
| Altitude reporting | Easy | Medium |
| Frequency changes between facilities | Medium | High |
| Traffic advisories (simulated) | Hard | Medium |

**Result**: Full VFR flight following from departure to destination

---

## Phase 5: Voice Improvements

**Goal**: More natural, varied voices

| Task | Difficulty | Impact |
|------|------------|--------|
| Multiple Piper voice models | Easy | Medium |
| Voice selection by facility type | Easy | Medium |
| Regional accent variation | Hard | Low |
| Faster TTS response time | Medium | High |

**Result**: Less robotic, more variety in controller voices

---

## Phase 6: IFR Operations (Advanced)

**Goal**: Instrument flight procedures

| Task | Difficulty | Impact |
|------|------------|--------|
| Navigation database (SIDs/STARs) | Hard | High |
| IFR clearance delivery | Hard | High |
| Approach clearances | Hard | High |
| Altitude/heading vectors | Medium | High |
| Missed approach procedures | Hard | Medium |

**Result**: Full IFR flight capability

---

## Phase 7: Living World (Long-term)

**Goal**: AI traffic and dynamic environment

| Task | Difficulty | Impact |
|------|------------|--------|
| Inject AI traffic | Very Hard | High |
| Traffic sequencing | Very Hard | High |
| Go-around vectors | Hard | Medium |
| Multi-frequency simulation | Hard | Medium |

**Result**: Full "Living World" experience with dynamic traffic

---

## Phase 8: Optimization & Modernization (Future)

**Goal**: Product-grade stability and performance

| Task | Difficulty | Impact |
|------|------------|--------|
| Rust Migration (Tauri/Iced) | Very Hard | High |
| WebAssembly Client | Very Hard | Medium |
| Cloud-sync preferences | Medium | Low |

**Result**: A high-performance, single-binary application with <50ms audio latency.

---

## Priority Order

1. **Phase 2** - Airport awareness (biggest gap right now)
2. **Phase 3** - Ground operations (makes it feel real)
3. **Phase 4** - VFR flight following (complete VFR experience)
4. **Phase 5** - Voice improvements (polish)
5. **Phase 6** - IFR (advanced users)
6. **Phase 7** - Living world (ambitious long-term)

---

## Data Sources Needed

| Data | Source | License |
|------|--------|---------|
| Airport database | FAA 28-day NASR | Public domain |
| METAR weather | aviationweather.gov | Public |
| Runway info | FAA APT.txt | Public domain |
| SID/STAR charts | FAA CIFP | Public domain |
