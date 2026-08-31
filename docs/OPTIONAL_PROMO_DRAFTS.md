# Optional: public build article (draft)

**Title:** Protocol 215 — Rehearsing clinical amendments before they reach a patient  

**Audience:** Builders at All Things Agentic / clinical-ops curious engineers  

**Outline**

1. **Hook:** Sites can run fragmented protocol versions for ~215 days.  
2. **Problem:** Amendments are release trains, not document diffs.  
3. **Approach:** Event-driven agent (Pub/Sub + ADK) with code-owned GREEN/AMBER/RED.  
4. **Gemini’s job:** Tool-less IR extraction with evidence—not authorization.  
5. **Demo story:** AURORA-101, Phoenix P002 courier conflict, human AMBER gate.  
6. **Honesty:** Synthetic only; hosted demo uses Live Gemini (see `docs/CLOUD_E2E_RESULTS.md`); local fake mode for CI.  
7. **Links:** https://github.com/0xyydeca/Protocol-215 · https://protocol-215-web-u6nfupvmhq-uc.a.run.app · *(video URL in Devpost)* · `docs/architecture.png`.  

**Do not claim:** validated clinical system, production-ready for real trials, perfect extraction.

---

# Optional: LinkedIn post (draft)

Rehearse the amendment before it reaches a patient.

Protocol 215 is our All Things Agentic (Taskmaster) build: an agentic preflight that compiles synthetic protocols, semantic-diffs changes, rehearses a Trial Twin, executes only safe GREEN actions, and pauses AMBER for a human—then ships a Release Manifest.

Why agentic, not a chatbot? Events, allowlisted tools, and policy in code—not free-form chat.

Synthetic data only. Not for real PHI or real trials.

#AllThingsAgenticHackathon #AgenticAI #ClinicalTrials #BuildInPublic

Repo: https://github.com/0xyydeca/Protocol-215  
Hosted: https://protocol-215-web-u6nfupvmhq-uc.a.run.app  
Video: *(Devpost only)*
