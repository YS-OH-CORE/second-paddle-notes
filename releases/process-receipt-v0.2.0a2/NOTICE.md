## Correction added 2026-09-11: receipt-finalization errors

A reporting defect in this older release is corrected in [Process Receipt 0.2.0a2](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/process-receipt-v0.2.0a2). After a child has run, failure during final receipt I/O can lose the structured observed outcome. The historical POSIX module CLI can incorrectly say `Process not launched`; the portable a1 command avoids that sentence but still lacks the corrected structured fallback. A receipt-close error can also skip restoring caller signal handlers. See [the reproduced fault and repair](https://github.com/YS-OH-CORE/second-paddle-notes/pull/12).

**Do not infer non-execution or automatically repeat work from a missing receipt or wrapper exit 2.** Inspect the destination and actual effects. The corrected version separates receipt failure from the already observed execution result; it does not undo work or guarantee durable error delivery.

This dated note is appended to the original release description. The assets, version tag and earlier notes remain unchanged; an old download does not silently contain the fix. The issue was verified using injected receipt-I/O faults around real inert child processes, not a claimed real-user incident.

한국어: 이 이전 버전은 실행 후 기록 저장이 실패하면 실제 실행 정보를 잃거나 잘못 안내할 수 있다. 0.2.0a2에 수정이 들어 있다. 기록이 없다는 이유로 이미 한 일을 자동으로 다시 실행하지 말고 실제 결과를 확인해야 한다. 기존 배포파일은 교체하지 않았으며 이 안내만 날짜를 붙여 추가했다.
