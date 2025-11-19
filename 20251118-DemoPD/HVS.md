HVS# HVS
**Hierarchical Voltage Encoding Scheme**
``` python
The Hierarchical Voltage Encoding Scheme

  Visual on Oscilloscope

  +2.5V ┤                                    ← STATE=5 (max normal state)
        │
  +2.0V ┤         ╔═══╗                     ← STATE=4 + status noise
        │         ║   ║
  +1.5V ┤    ╔════╝   ╚════╗                ← STATE=3 + status noise
        │    ║              ║
  +1.0V ┤  ══╝              ╚══              ← STATE=2 + status noise
        │  ░░░░░░░░░░░░░░░░░░░              (░ = 8-bit status "noise" ±50mV around base)
  +0.5V ┤══                                  ← STATE=1 + status noise
        │
   0.0V ┼══════════════════════════════════ ← STATE=0 (IDLE) + status noise
  ─────────────────────────────────────────
  -0.5V ┤         ═══                       ← FAULT! (negative voltage, magnitude shows last state)
        │
  -2.0V ┤═══                                ← FAULT from STATE=4

  Key Properties:
  - 200mV steps = Major state transitions (human-readable)
  - ±50mV "noise" = 8-bit status encoded as fine-grained voltage variation
  - Negative voltage = Fault condition (APP:STATUS[7] = 1)
  - Magnitude preserved = Last normal state visible even in fault
```

---

## What is HVS?

The **Hierarchical Voltage Encoding Scheme** packs 14 bits of FSM information (6-bit state + 8-bit app status) into a single oscilloscope channel using a clever two-level voltage encoding:

### **Level 1: Major State Transitions (200mV steps)**
Each FSM state increments the base voltage by 200mV, creating visually distinct "stairsteps":
- State 0 (IDLE): 0.0V base
- State 1 (ARMED): 0.2V base
- State 2 (FIRING): 0.4V base
- State 3 (COOLDOWN): 0.6V base

This gives you **12 distinct states** in the 0-2.5V range, clearly visible on any oscilloscope.

### **Level 2: Status "Noise" (±100mV fine detail)**
Around each base voltage, the 8-bit application status creates fine-grained variation:
- 7 bits of payload: counter values, error codes, flags
- 1 bit (STATUS[7]): fault indicator

Status bits 6:0 encode 0-127 values as 0-100mV offset (0.78mV per step), appearing as subtle "fuzzy" voltage around each state level.

### **Fault Detection: Sign Flip**
When STATUS[7]=1 (fault detected), the entire voltage goes **negative**:
- Normal: State 2 + status 0x12 → +0.414V
- Fault: State 2 + status 0x92 → **-0.414V**

The magnitude preserves the last known state, so you can debug "we were in state 2 when the fault occurred."

### **Decoding Example**
```python
voltage = 0.414  # Read from oscilloscope

state = int(voltage / 0.2)          # → 2 (FIRING)
status_offset = (voltage - 0.4)     # → 0.014V (14mV)
status_lower = int(14 / 0.78)       # → 18 (0x12)
fault = voltage < 0                 # → False
```

### **Why This Works**
- **Human-readable**: 200mV steps are obvious on scope (no decoder needed for states)
- **Machine-decodable**: Simple arithmetic extracts full 14-bit payload
- **Zero LUTs**: Pure arithmetic in VHDL (no lookup tables)
- **Train like you fight**: Single bitstream for dev and production
- **Fault diagnosis**: Negative voltage is unmistakable error indication

### **FORGE Standard**
All FORGE applications **must** export:
- `app_state_vector[5:0]` - FSM state (linear encoding 0-31)
- `app_status_vector[7:0]` - App-specific status (bit 7 = fault)

The SHIM layer automatically encodes these into OutputD using HVS, making FSM state + status visible on any oscilloscope without special tooling.

---

**Related Documents:**
- `Obsidian/Project/Handoffs/2025-11-07-handoff-6-hierarchical-voltage-encoding.md` - Implementation plan
- `Obsidian/Project/Review/HIERARCHICAL_VOLTAGE_ENCODING_ALTERNATIVES.md` - Design rationale (why 200mV vs 100mV/250mV/500mV)