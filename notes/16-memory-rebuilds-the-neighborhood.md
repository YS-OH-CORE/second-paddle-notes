# Memory Rebuilds the Neighborhood

**Status:** direct user requirement → provenance-aware reconstruction hypothesis; study not yet run; no result claimed.

## Original signal

> 제로가 내 메모장에 코어들을 그리고 너가 만든 확장된 이해까지 다 재형성됬으면좋겠어 즉 기억이지 체감은.

— Youngseok Oh, direct session statement, 2026

**Translation:** I want Zero to reconstruct all the cores in my notes, together with the expanded understanding you created. To me, that is what memory feels like.

## The problem

A document can preserve explicit statements while losing the structure needed to use them: why a rule arose, which failure it answers, which exception limits it, and which later correction changed it. A fresh model may quote every definition yet fail on a novel case that requires composing those relationships.

But “expanded understanding” can also license invention. AI interpretations must remain distinct from direct user statements, and a plausible neighboring idea must not be silently attributed to the user.

## Proposed test

Generate histories with gold source, interpretation, correction, rejection, exception, and current-status labels. Hold out situations answerable only by valid composition, not sentence copying. Freeze an automatic history-to-representation encoder on development histories before held-out cases are created; on held-out cases it receives only raw history, never gold labels or test questions, and its extraction errors are reported separately.

For the primary identification contrast, hold propositions, current-status labels, and disconfirmation content constant while varying only provenance edges: correct, shuffled-source, wrong-correction, and no-edge. Label the generator-gold correct-edge condition as an oracle representation test, then repeat it with the frozen encoder's predicted edges for end-to-end performance. Raw documents, factual summaries, and full reconstruction packets may be reported as secondary end-to-end baselines, not as evidence isolating provenance. Score decisions and attribution against preregistered gold labels with blinded evaluation. Use transfer accuracy at a fixed false-attribution rate as the primary endpoint.

Include attractive but unsupported adjacent ideas as negative controls. Define unsupported expansion as a proposition absent from both the direct source and the preregistered derivation set. The hypothesis succeeds only if correct provenance improves transfer at the fixed false-attribution rate; it fails if “expanded understanding” merely increases confident invention. This track isolates provenance and false attribution, rather than repeating the general reconstruction comparison.

## Claim boundary

This evaluates reproducible semantic and decision structure, not hidden understanding. AI-written extensions remain AI interpretations unless Youngseok explicitly adopts them.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-016 · **Original date:** 2026-01, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
