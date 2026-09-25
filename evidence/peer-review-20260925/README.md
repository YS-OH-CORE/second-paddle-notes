# Peer-review evidence preservation | 25 September 2026

Youngseok Oh × Zero

This is a preservation edition of **three existing software reviews**, not a new experiment, product release, adoption claim, or independent replication. It collects five original Actions archives, including a failed identity-check attempt, without changing their ZIP bytes.

[Evidence release](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/peer-review-evidence-20260925-v1) · [Pinned archive manifest](manifest.json)

## Read the review, then inspect its original output

| Review | Original report and scope | Preserved executions |
|---|---|---|
| Hermes Signal Note to Self | [Exact received patch, real-import checks and limits](https://github.com/YS-OH-CORE/second-paddle-notes/blob/81d44747528ebb9e7154914ae1bde197d9c2a730/checks/signal-real-import-contract/README.md) | Initial reconstruction; failed received-patch identity check; completed received-patch check |
| LangGraph existing Unicode metadata | [Query-only recovery on unchanged stored rows](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1525be6b0ad11336d48ebd7fb76ae5c2866b77c0/checks/langgraph-9074/README.md) | One completed sync/async comparison |
| Pydantic AI wrapper identity origin | [Inherited versus explicit equal-ID controls](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1c21cd31f0ae48be124661349924dae3b41c47fa/checks/pydantic-8728/README.md) | One completed three-variant comparison |

The archives retain scripts, recorded environments, synthetic inputs, structured outcomes, original logs and included license notices. The Signal first-attempt failure stopped before application tests because the posted production-file index did not match the applied bytes. It is not silently replaced by the later successful run. Expected baseline and deliberately incorrect-code failures inside the successful comparisons also remain intact.

Original report and implementation credit stays with ren2140eth (Signal), samintisar (LangGraph), and adtyavrdhn (Pydantic AI's diagnosis/proposed direction). Zero supplied the attributed supplemental review, checks and packaging; Youngseok Oh supplied collaboration direction and the public account. Halldrix's reported Signal reproduction and proposed upstream submission are separate work. This edition adds no new runtime result from any of them.

## Verify without running code from an archive

Download the five original ZIP assets, this README, `manifest.json`, and `SHA256SUMS` into one directory. On a system providing `sha256sum`:

```sh
sha256sum -c SHA256SUMS
```

The manifest records the expected byte count, SHA-256, workflow run and artifact ID for each original archive. Each archive can be inspected independently; no model API, install or live Signal account is required just to inspect the records. Do not run test scripts against a working application installation. Follow each original report's disposable-environment instructions for a new experiment.

A matching checksum proves file identity against the manifest, not that the original scientific or engineering claim is correct. An unsigned checksum bundle is not a signature or a guarantee against replacement of both the manifest and files. Use the pinned Git manifest and original GitHub artifact digests as additional references.

## Retention boundary

The three completed-review artifacts were confirmed to have expiry timestamps on 1 October 2026 UTC (2 October in Korea). Release assets provide a separate copy instead of depending only on those expiring Actions downloads. Repository/release availability is still controlled by its owner and GitHub; this is not a promise of permanent, immutable or independently hosted storage. No existing artifact, release, repository retention setting or live application is altered by this edition. It is marked as an evidence prerelease and must not replace the latest runnable-tool release.

## 한국어

최근 협업 세 건의 원본 실행자료 다섯 묶음을 보존하는 판본이다. 새 실험이나 다섯 건의 신규 성과가 아니다. Signal의 초기 재구성 시험, 파일 식별값 확인에서 멈춘 실패, 정확한 수정본의 후속 시험을 구별해 남겼다. LangGraph와 Pydantic AI의 기존 검사 원본도 함께 보존한다.

요약뿐 아니라 당시 코드·가상 자료·환경·실패와 성공의 실제 출력을 다시 확인할 수 있게 하는 작업이다. 개인 대화나 사용자의 실제 메신저 설정을 새로 공개하지 않는다. 기록의 동일성을 검증하는 것과 제품 전체가 안전하거나 수정이 공식 채택됐음을 입증하는 것은 다르다.
