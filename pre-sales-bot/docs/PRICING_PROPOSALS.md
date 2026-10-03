# Phase 5 Proposals: Pricing & Config Hardening (Owner Review)

> **Status**: PROPOSAL ONLY (per AGENT_BRIEF.md Phase 5 guidelines — do not merge into engine without explicit owner approval).
> Existing `pricing.yaml` and `pricing.py` remain untouched and strictly preserved.

---

## 1. Optional Cap on Compounded Flag Multipliers

### Current Behaviour
In `pricing.py:27-31`, every detected flag multiplier is multiplied together without a cap:
```python
flags_factor = 1.0
for flag in flags:
    flags_factor *= multipliers.get("flags", {}).get(flag, 1.0)
```
If a client brief selects `auth` (1.08), `admin` (1.12), `realtime` (1.18), `marketplace` (1.28), and `ai_features` (1.22):
$$\text{Compounded Factor} = 1.08 \times 1.12 \times 1.18 \times 1.28 \times 1.22 \approx 2.23$$
Together with mobile both platforms ($1.32$) and integrations ($1.28$), the overall multiplier exceeds **$3.76\times$** the base price.

### Proposed Improvement
Add an optional `max_flags_factor: float = 2.0` (or `max_compounded_multiplier: float = 3.0`) in `pricing.yaml`:
```yaml
# config/pricing.yaml proposal:
max_flags_factor: 2.0
```
And in `pricing.py`:
```python
flags_factor = min(flags_factor, pricing.max_flags_factor or 2.0)
```
**Rationale**: Prevents sticker shock for feature-rich MVPs while still fairly compensating for scope complexity.

---

## 2. Dynamic Band Width Based on Discovery Completeness

### Current Behaviour
The price band is low = 0.8 x raw and high = raw (width 25% of low, 0% above raw) (`low_side_factor: 0.80`, `range_factor: 1.25`) regardless of how complete the client brief is (`pricing.py:52-53`).
Notice that because `low = round(raw * 0.80)` and `high = round(low * 1.25) = round(raw * 0.80 * 1.25) = round(raw * 1.0)`, the high estimate equals the raw calculated estimate, and the spread width is $(1.0 - 0.8) / 0.8 = 25\%$ of the low figure (0% above raw).
Whether the visitor answered only 1 question or all 7 discovery questions, the spread remains identical.

### Proposed Improvement
Introduce confidence-driven band width:
- **Early / Incomplete Brief (1–3 slots filled or visitor selected "not sure")**:
  - Wider range: low = 0.70 x raw and high = raw (width 42.8% of low, 0% above raw; `low_side_factor: 0.70`, `range_factor: 1.428`) to indicate higher scoping uncertainty.
- **Detailed / Complete Brief (all critical slots filled)**:
  - Narrower range: low = 0.90 x raw and high = raw (width 11.1% of low, 0% above raw; `low_side_factor: 0.90`, `range_factor: 1.111`) to reflect precise scoping.

**Rationale**: Sets realistic expectations early in the conversation without misleading prospective clients on precision before requirements are clarified.

---

## 3. Multi-Currency Display (USD / INR) Driven by Config, Never by LLM

### Current Behaviour
Currency is USD-only in `pricing.yaml` (`currency: USD`). The LLM is strictly prohibited from converting currency to prevent hallucinations and inconsistent exchange rates.

### Proposed Improvement
Add explicit currency rates and formatting rules to tenant `pricing.yaml`:
```yaml
# tenants/demo/pricing.yaml:
currencies:
  USD:
    symbol: "$"
    rate: 1.0
    rounding: 500
    format: "${amount:,}"
  INR:
    symbol: "₹"
    rate: 95.0
    rounding: 50000
    format: "₹{amount:,}"
default_display_currency: "USD"
```
And calculate dual-currency labels deterministically in `pricing.py`:
```python
# $24,000 – $30,000 (approx. ₹22.8L – ₹28.5L INR)
```
**Rationale**: 100% deterministic arithmetic in code, 0% hallucinations from the LLM, with full tenant flexibility for global vs domestic clients.
