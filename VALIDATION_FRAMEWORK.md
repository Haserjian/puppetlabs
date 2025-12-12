# Quintet ↔ Loom Integration Validation Framework

**Purpose:** Systematically answer: Does the Quintet-Loom integration work end-to-end?

**Last Updated:** 2025-12-09

---

## Status Summary

| Aspect | Status | Evidence | Risk |
|--------|--------|----------|------|
| **Unit Tests** | ✅ PASS | 22/22 tests passing (0.37s) | None |
| **Sample Data** | ✅ EXISTS | 45 episodes in fixture JSON | Low |
| **Adapter Code** | ✅ EXISTS | loom_adapter.py + receipt_persistence.py | Medium |
| **Loom Integration** | ❓ UNKNOWN | Code written, not validated on real Loom | High |
| **Real Data** | ❌ MISSING | No ccio-data directory | High |
| **Operator Tooling** | ✅ PARTIAL | Scripts exist, unclear if production-ready | Medium |

---

## What We Know Works

### 1. Episode → Recommendation Pipeline ✅

```
LoomEpisode (JSON)
      ↓
analyze_episodes()
      ↓
PolicyRecommendation (PROMOTE | HOLD | ROLLBACK)
```

**Evidence:** Test `test_analyze_episodes_recommends_promote` PASSES
**What it does:** Loads 45 synthetic episodes, stratifies by mode/domain, returns recommendation

### 2. Stress Testing Gate ✅

```
PolicyRecommendation
      ↓
run_pre_promote_check()
      ↓
✓ (stress tests pass) or ✗ (blocked)
```

**Evidence:** Tests `TestPrePromotionStressGate` all PASS
**What it does:** Before promoting, validates against stress scenarios

### 3. Receipt Chain Integrity ✅

```
Recommendation
      ↓
generate_receipts()
      ↓
Append-only JSONL with hash chain
```

**Evidence:** Test `test_receipt_chain_can_be_audited` PASSES
**What it does:** Creates cryptographic audit trail

### 4. Error Handling ✅

**Evidence:** Tests in `TestErrorHandlingAndEdgeCases` all PASS
**What it does:** Handles malformed data, missing files, concurrent access

---

## What We Don't Know (The Gaps)

### Gap 1: Real Loom Data Integration ❓

**Question:** Does this work on actual Loom episodes (not test fixtures)?

**Why it matters:** Test data is synthetic. Real Loom episodes may have:
- Different JSON schema
- Missing fields
- Unexpected data types
- Different stratification keys

**How to validate:**
1. Export real episodes from a Loom instance
2. Run Quintet analysis on them
3. Verify recommendations make sense (not random)
4. Trace one episode through the full pipeline

**Risk level:** HIGH (untested path)

---

### Gap 2: Loom Applying Recommendations ❓

**Question:** Can Loom actually receive and apply Quintet's recommendations?

**Why it matters:** We have the adapter, but is it:
- Plugged into Loom's actual policy update code?
- Handling the recommendation format correctly?
- Monitoring outcomes after promotion?

**How to validate:**
1. Trace Loom's daemon code to see if it calls Quintet
2. Verify policy update logic consumes recommendation format
3. Run a full cycle: episode → recommendation → policy change → new episode
4. Measure if predicted outcome matches actual outcome

**Risk level:** HIGH (integration point untested)

---

### Gap 3: Causal Analysis Quality ❓

**Question:** Are Quintet's recommendations actually *good*?

**Why it matters:** System might recommend changes that:
- Improve metrics but violate dignity constraints
- Show statistical noise as signal
- Transfer poorly across patient populations
- Revert beneficial prior policies

**How to validate:**
1. Take 10 recommendations from real data
2. For each: explain WHY Quintet made it (trace the causal reasoning)
3. Verify the stratification keys are appropriate (not confounding)
4. Check if recommendation would revert a known good policy
5. Score recommendations on: confidence, robustness, safety

**Risk level:** MEDIUM (quality vs. correctness)

---

### Gap 4: Operator Experience ❓

**Question:** Can a human operator actually use this system?

**Why it matters:** Code exists, but is it:
- Easy to understand?
- Safe to operate?
- Giving clear feedback?
- Handling failures gracefully?

**How to validate:**
1. Read the operator cheatsheet and scripts
2. Walk through a full scenario as an operator
3. Simulate error cases (Quintet unavailable, bad recommendation, etc.)
4. Measure decision time (can operator decide to promote in < 5 min?)

**Risk level:** MEDIUM (UX/ops readiness)

---

### Gap 5: Production Readiness ❓

**Question:** Is this safe to deploy to real Loom?

**Why it matters:** Production needs:
- Rollback procedure if Quintet breaks
- Monitoring + alerting
- Failure modes documented
- Team trained on how to operate

**How to validate:**
1. Write deployment checklist
2. Document failure modes + recovery procedures
3. Set up monitoring (recommendations, promotions, rollbacks)
4. Create runbooks for common problems

**Risk level:** HIGH (operations not yet designed)

---

## Validation Roadmap (Recommended Order)

### Phase 1: Real Data (Days 1-2)

**Goal:** Prove system works on actual Loom data

- [ ] Export 100 real Loom episodes (or synthetic if unavailable)
- [ ] Run Quintet analysis on them
- [ ] Spot-check 5 recommendations (make sense?)
- [ ] Trace one episode through full pipeline (receipt chain, stress gate, output)
- [ ] Document any schema mismatches or bugs

**Output:** "Real data validation report"

---

### Phase 2: Integration (Days 3-4)

**Goal:** Prove Loom can consume Quintet's recommendations

- [ ] Verify Loom daemon has hook to call Quintet
- [ ] Run full cycle: episode → recommendation → policy change → monitor
- [ ] Measure: Does predicted outcome match actual?
- [ ] Document any API mismatches or data loss
- [ ] Create integration test with real Loom daemon

**Output:** "Integration validation report"

---

### Phase 3: Quality (Days 5-6)

**Goal:** Prove recommendations are actually good

- [ ] Pick 10 recommendations from real data
- [ ] For each: trace the causal reasoning
- [ ] Score on: confidence, robustness, safety
- [ ] Identify any obvious bad recommendations
- [ ] Document bias or confounding in stratification

**Output:** "Recommendation quality report"

---

### Phase 4: Operations (Days 7-8)

**Goal:** Make it safe and usable

- [ ] Write deployment checklist
- [ ] Document failure modes + recovery
- [ ] Set up monitoring + alerting
- [ ] Create operator runbooks
- [ ] Walk through scenario with someone (not you)

**Output:** "Operations readiness report"

---

## Tests That Pass (22 total)

```
✅ test_load_episodes_from_json
✅ test_stratify_episodes_by_mode_and_domain
✅ test_analyze_episodes_recommends_promote
✅ test_analyze_episodes_respects_guardrails
✅ test_analyze_episodes_insufficient_data_holds
✅ test_generate_receipts_from_recommendation
✅ test_stress_gate_blocks_unsafe_change
✅ test_stress_gate_with_passing_scenarios
✅ test_stress_gate_with_failing_scenarios
✅ test_get_scenarios_for_lever_returns_correct_gates
✅ test_structured_pre_promote_check_result
✅ test_generate_multiple_experiment_receipts
✅ test_receipt_chain_can_be_audited
✅ test_shadow_executions_form_valid_chain
✅ test_experiment_registry_persists_data
✅ test_complete_policy_promotion_flow
✅ test_hold_on_stress_gate_failure
✅ test_empty_episode_list
✅ test_episodes_missing_policy_data
✅ test_malformed_episode_data
✅ test_stress_gate_with_missing_scenario_file
✅ test_experiment_registry_concurrent_access
```

---

## Critical Unknowns

1. **Do real Loom episodes have the expected schema?**
2. **Is Loom daemon actually calling Quintet?**
3. **Are recommendations actually improving Loom's performance?**
4. **Can operators understand and safely apply recommendations?**
5. **What breaks when Quintet is unavailable?**

---

## Next Steps

Pick one:

**Option A (Fastest validation):**
- Run Phase 1 only (real data test)
- Takes 2 days
- Answers: "Does it work on real data?"

**Option B (Complete validation):**
- Run all 4 phases
- Takes 8 days
- Answers: "Is it production-ready?"

**Option C (Critical path):**
- Run Phase 1 + 2 (data + integration)
- Takes 4 days
- Answers: "Does end-to-end work?"

**Recommendation:** Start with Option C (Phase 1+2). If those pass, you know the system is fundamentally sound. Then decide on Phase 3+4 based on whether you actually want to deploy it.

---

## Success Criteria

You can claim "Quintet-Loom integration works" when:

- ✅ Real episodes run through the pipeline without errors
- ✅ Recommendations are made and can be traced (why this recommendation?)
- ✅ Recommendations are passed to Loom and applied
- ✅ Monitoring shows predicted outcome ≈ actual outcome (within 10%)
- ✅ No critical bugs found in integration
- ✅ Operator can safely decide to promote/hold/rollback

**Current status:** 0/6 ✅ (unknowns)

