# Questions for ChatGPT — Round 7+ (browse GitHub Markdown)

**Please open and read (do not ask for uploads):**

- Folder: https://github.com/Coucou2016/river-carbon-transport/tree/main/docs/chatgpt/
- Raw (optional):  
  - https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/docs/chatgpt/00_TASK_BRIEF.md  
  - https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/docs/chatgpt/01_PAPER_CURRENT.md  
  - https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/docs/chatgpt/02_REPORT_VS_PAPER_AUDIT.md  
  - https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/docs/chatgpt/03_DATA_INTEGRITY_CHECKLIST.md  
  - https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/docs/chatgpt/04_QUESTIONS_FOR_CHATGPT.md  
- Also: https://github.com/Coucou2016/river-carbon-transport/blob/main/paper.md  
- Framework: https://github.com/Coucou2016/river-carbon-transport/blob/main/docs/PAPER_FRAMEWORK.md  
- Prior rounds: https://github.com/Coucou2016/river-carbon-transport/blob/main/docs/REVIEW_ROUNDS.md  

**Web search:** ON (EMS writing craft; Markovich/Bennett/Vilas exemplars).  
**Constraint:** Never invent metrics; never invert Residual-AI vs Baseline; keep F_CO₂ as model diagnostic.

---

## Round 7 — Paper↔report leakage + missing pieces + unreal claims

Please answer numbered:

1. After reading `02_REPORT_VS_PAPER_AUDIT.md`, list every leakage item you agree must leave the **paper**, and anything you think may remain if rephrased academically.
2. Scan `01_PAPER_CURRENT.md` + `paper.md` for **unreal / overclaimed / inconsistent** statements vs the immutable metrics in `00_TASK_BRIEF.md`. Quote the risky phrase and prescribe the fix.
3. What **missing pieces** still block EMS submission (content, not LaTeX formatting)? Separate into (a) must-fix text now, (b) 待补充 author/data items, (c) deferred code experiments.
4. Recommend a clean **paper vs report** division of labor for figure captions (journal caption vs teaching five-part notes).

---

## Round 8 — Submission-quality Abstract / Intro / Discussion

5. Using Markovich (2022) / Bennett (2013) / Vilas (2023) argument architecture (web search OK), return:
   - English Abstract ≤250 words (EMS methods/diagnostics voice)
   - Optional Chinese Abstract twin
   - Revised Introduction (≈4–6 paragraphs) imitating EMS evaluation papers
   - Discussion subsection headings + 1 short paragraph each (keep negative result + equifinality)
6. Explicitly demote LES-analog and “physics-constrained ML” from headlines if still present.
7. Provide 3 Highlights (≤85 chars each ideal) consistent with frozen metrics.

Return **revised prose as text** for Cursor to merge. Do not invent numbers.

---

## Round 9 — Data integrity + Methods/Results consistency

8. Walk `03_DATA_INTEGRITY_CHECKLIST.md`: which items must become **待补充** in Methods/Data availability, and which are already correctly handled?
9. Propose Methods wording (no script filenames) for: c_in fallback; Y→X filter order; logical vs NHD topology; width proxy; F_CO₂ diagnostic; “not nested CV.”
10. Check Results lead order vs H1/H2/H3 falsification tests — any reordering needed?

---

## Round 10 (optional) — Referee pass after Cursor implements

11. After Cursor pushes revised `paper.md` / briefs, simulate EMS referee: recommendation, Major/Minor, mandatory text changes, what NOT to change (especially negative Residual-AI result).

---

## Response format requested

For each round, use:

```
VERDICT: ...
BROWSED: [list GitHub URLs you opened]
ACCEPT_NOW: ...
DEFER: ...
REJECT_IF_CLAIMED: ...
PROSE_TO_MERGE: ...
```
