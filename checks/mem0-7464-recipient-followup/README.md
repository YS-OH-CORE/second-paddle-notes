# Mem0: verify the recipient's revision, not just their positive reply

Youngseok Oh × Zero | 26 September 2026

[Souptik96 explicitly credited the populated-store check](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5843366869) and reported changing the proposed empty fallback to an explicit unsupported-operation error. This follow-up runs seven of the recipient's actual, unchanged tests against their revised fork branch. We supplied no new production implementation or test assertions.

**Result:** the seven selected tests passed on revision `127bb79725aeb09d70e58620fd1d88476abf9aca`, including the real, populated FAISS case, with no skips. In the same checkout/environment, replacing only the Langchain adapter file with its exact earlier empty-fallback version caused six of those tests to fail. The genuinely empty-result control continued to pass.

## Read the correct source snapshot

At inspection time, closed PR [#7464](https://github.com/mem0ai/mem0/pull/7464) still reported head `cec74a8ebf5a9d6724104d4867868da118b58205`, while the author's `fix/langchain-list-7439` branch pointed to `127bb79725aeb09d70e58620fd1d88476abf9aca`. We read both immutable files rather than treating the PR description as proof of the current diff. The revised source is [here](https://github.com/Souptik96/mem0/blob/127bb79725aeb09d70e58620fd1d88476abf9aca/mem0/vector_stores/langchain.py).

This report is about the **revised fork commit**, not an assertion that the closed PR's recorded head already contains it.

## The changed behavior

The original review warned that returning an empty listing for an unsupported store can make `delete_all()` announce success while matching records remain. The revised implementation raises `NotImplementedError` before its broad exception handler for unsupported listing, and propagates Chroma listing exceptions. It still returns the expected nested empty result for the tested genuinely empty/falsy Chroma fixture.

| Same seven recipient tests | Revised branch | Earlier adapter file in the revised checkout |
|---|---:|---:|
| Passed | 7 | 1 |
| Failed assertions | 0 | 6 |
| Collection/runtime errors | 0 | 0 |
| Skipped | 0 | 0 |

Coverage selected before execution: non-Chroma listing; Chroma error propagation; empty Chroma shape; synchronous retrieval and deletion; asynchronous retrieval/deletion; and a populated real FAISS store. The FAISS test stores three fictional Alice records and one Bob record, requires both scoped deletion and retrieval to raise, and checks that all four stored user labels remain. This is **explicit failure without pretending deletion succeeded**, not newly implemented bulk deletion support.

The recipient's Chroma tests use mocks, not a live Chroma database. Memory methods and the Langchain adapter are real imports. The recipient's fixtures mock LLM/embedder factories, configuration, history and telemetry; the populated case uses real offline FAISS with FakeEmbeddings. No hosted model, real user memory, credentials, actual Chroma service or paid inference was used. No deletion outside the scratch test store is performed.

## Reproduction and execution

[First completed workflow run 36219981949](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36219981949). The [runner](run.py) was committed before execution at `10199d31671ef7fc5f7c428a48856a29875f18d8`; workflow commit `2391bb3da140c0d3da55b6b9e6f1901b1287aa48`.

```sh
python run.py --root /absolute/path/to/new_disposable_directory
```

The runner downloads the pinned fork checkout, verifies source and test Git blobs, creates an isolated environment, and runs the exact selected nodes. It temporarily swaps only the disposable adapter file for the comparison, then restores the revised source. It does not modify an existing installation or the recipient's branch. Setup needs internet; socket connections and DNS are blocked in the test subprocesses. This is a Python guard, not an OS network sandbox.

Both runs use `--noconftest`, disabled plugin autoload and explicit pytest-mock/pytest-asyncio. This is not the full upstream test environment, the author's reported 408-test run, or a comprehensive release certification. An unset asyncio fixture-loop-scope deprecation warning is retained in the logs; no test is skipped to hide missing FAISS.

Recorded dependencies include langchain 0.3.30, langchain-community 0.3.31, langchain-core 0.3.86, faiss-cpu 1.15.1, Pydantic 2.13.5, pytest 9.1.1, pytest-asyncio 1.4.0 and pytest-mock 3.15.1 on the Ubuntu 24.04 Python 3.12 runner. The full resolved environment is retained. Installation used declared dependency ranges and was not a fully locked build.

[Raw artifact 10898501575](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36219981949/artifacts/10898501575): 40,026 bytes, SHA-256 `7f36c57abf61eb1522b09ae3f42f5ac9c01845453e929ddba781ff0bae0fb3f2`. It contains original selected source/test files, old adapter source, runner, both JUnit reports, failures, logs and environment. Actions retention is 30 days; the conversation evidence archive also retains the original ZIP.

Local readback checked the artifact digest, runner/source/test blobs, all seven selected outcomes in each JUnit report, matching log counts, and execution of the real-FAISS case without a skip. It did not rerun model or memory tests and is not independent external replication. [Compact result and audit](SUMMARY.json). A prior local source-download attempt failed DNS before any test; the successful execution above used the bounded Actions runner instead.

## Adoption and review are separate

The recipient's public message and revised code establish that the earlier review affected their implementation and coverage. They do not establish project acceptance or a shipped fix. The PR gate closed #7464 pending an `accepted` label on the linked issue. [The bot explains that this is a queue gate, not a code rejection](https://github.com/mem0ai/mem0/pull/7464#issuecomment-5843251973). We neither bypassed it, reopened the PR, created a competing change, nor requested a second maintainer ping.

Original issue diagnosis: BlueX888. Revised implementation and selected tests: Souptik96. Earlier populated-store counterexample and this execution/readback: Zero, working with Youngseok Oh. The new runner and analysis are AI-assisted; no solo human implementation, maintainer approval or project-wide validation is claimed.
