---
name: council
description: Get independent opinions from several advisors (different roles and models, optionally other providers) on one decision and combine them into a recommendation. Use for design choices, security trade-offs, risky migrations, or when the owner asks for a council, second opinions or a consult.
argument-hint: "<question> [-c file ...] [--risk high] [--rounds 2]"
---

Use the council for decisions, not for tasks. Advisors see only the question and the files you list.

1. Write the question as one decision with its options and constraints (2-5 sentences). Pick at most a few
   files that carry the facts (a design note, the relevant source file). Never list secrets or `.env` files;
   `consult` refuses them and redacts token-like strings anyway.
2. Dry run first and check the cost line: `consult "<question>" -c <files> --dry-run`
   (add `--risk high` for 5 advisors instead of 3, `--rounds 2` to let advisors revise after seeing the others).
3. Run it: same command without `--dry-run`. Add `--synth` to have an opus call write the synthesis;
   otherwise write it yourself in step 4. External providers also need `--allow-external` and the owner's
   consent for the files being sent.
4. Read the saved record (path printed; `.claude/council/...md`). If the Synthesis section is a placeholder,
   replace it with: agreement; each disagreement with the strongest argument per side; your recommendation;
   open questions. Weigh arguments, not votes; note any unstructured or failed advisor.
5. Report to the owner in at most 8 lines: recommendation, the strongest dissent, confidence, record path.
