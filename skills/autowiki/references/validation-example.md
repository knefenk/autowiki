# autowiki  -  Validation Example (Worked Case)

## The claim

From the ENPIRE paper abstract:

> "Powered by ENPIRE, frontier coding agents can autonomously develop a policy
> to achieve a 99% success rate on challenging, dexterous manipulation tasks
> in the real world."

## Source fidelity check

1. Re-read the source section. The paper states this in the abstract.
2. Check: same numbers? 99%  -  yes.
3. Check: same qualifiers? The paper later reveals this is **pass@8**, not pass@1.
   A 13% pass@1 policy can hit 99% pass@8. The abstract doesn't mention this.
4. Check: same context? The sim reproduction (skr3178/ENPIRE) reached ~50%
   held-out, not 99%. Real-world Push-T caused 2 of 3 agents to fail.

**Result:** Claim is faithful to the abstract text but the abstract omits
important qualifiers. Set `confidence: medium`. Add note:

> "Confidence: medium  -  the claim is from a credible source but is qualified
> by pass@8 semantics and not consistently reproduced. The sim reproduction
> reached ~50% held-out, not 99%."

## The confidence score

| Criterion | Assessment |
|---|---|
| Source count | 1 (the paper itself) |
| Contradictions | None in KB yet |
| Fidelity | Abstract faithful, but qualifiers omitted |
| Is opinion? | No (empirical claim) |

→ `confidence: medium` (single source, qualified claim, not consistently reproduced)

## What the lint would flag

During a lint pass, this page would appear in:
- **Heuristic checks (report-only):** "Claims about metrics need qualification
  scrutiny. The 99% figure is pass@8, not pass@1. Consider reviewing."
- **Low/medium confidence pages:** listed for human review
