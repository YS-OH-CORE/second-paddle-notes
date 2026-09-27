# Source acquisition attempt history

The first hosted job, run 36358248219 / job 108730150823, installed the test dependencies but stopped before source extraction and before any pytest case: the complete upstream ZIP exceeded the registered 64 MiB bound. This is a setup failure, not a Honcho regression or a completed runtime test.

The second attempt changes source acquisition only: a shallow, blob-filtered sparse Git checkout requests source/config file types and excludes tests/website media. Selected source still has a 64 MiB limit; metadata size and source byte count are reported separately. No global Git settings, repository credentials or user PC are used. The pinned upstream commit and three verified source blobs, four test cases and two local detector mutants are unchanged.

The workflow permits one synchronize transition from the initial evidence commit ea01c300d4791e9a1a4d7e211cc7a0e327dc1f14. Later result edits do not repeat it. Both hosted attempts remain visible. No runtime pass is asserted until actual case results are available.
