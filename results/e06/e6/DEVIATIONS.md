# E6 deviations

| UTC | Change | Reason | Model output existed? |
|---|---|---|---|
| 2026-09-19T22:20:58Z | `e6/PROTOCOL_FREEZE_E6.md` first written and hashed (`9d20cd63954ed56978819d7c01dc5428a3c4860b9d6998b6906b37d9bcd81652`). | Freeze before any output. | No |
| 2026-09-19T22:29Z | Added §1.0 "Who sees the fact": the receiver's first user turn keeps the **original, fact-free** question block, so only the helper sees `fact1`. File re-hashed; new SHA-256 in `PROTOCOL_FREEZE.sha256`. | The frozen `T2TReceiverBundle.consume` rebuilds the first user turn from the helper's question block. Passing the fact-augmented block would also change the **receiver's** prompt, which the task requires to stay byte-identical, and would let the receiver read `fact1` directly instead of through the helper's message. Stated explicitly rather than left implicit in the code. | **No** — no E6 model output existed at this time. |
