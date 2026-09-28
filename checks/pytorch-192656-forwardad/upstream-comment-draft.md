> **AI-assisted analysis and bounded CPU verification**
>
> The fresh tangent wrapper in `FunctionalTensor.unpack_dual` appears to lose an intermediate mutation dependency. With the two changed runtime Python files from `eb9c90dd1f2b67cadf9f7681176f1b5fab074423` loaded over a fixed `torch==2.13.0+cpu` wheel, this function returns a different **output tangent** under internal `dispatch_functionalize` than in eager execution:
>
> ```python
> def f(dual):
>     work = dual * 2
>     fwAD.unpack_dual(work).tangent.add_(10)
>     return work * 3
> ```
>
> For float64 primal `[1., 2.]` and input tangent `[3., 4.]`, both paths return primal `[6., 12.]`, but eager returns tangent **`[48., 54.]`** and the functionalized path returns **`[18., 24.]`**. Both input tensors' values remain unchanged. Mutation is on `work`, avoiding `dispatch_functionalize`'s input-mutation propagation exception.
>
> The four-test comparison records **3 passes and 1 assertion failure** on these candidate files: the eager analytic oracle, read-only inspection, and mutation of an explicit tangent clone pass; only the intermediate tangent-mutation comparison fails. With the corresponding files from parent `061ace3a865340a4f6a351e5ef8f3a7f37b6645e`, the eager oracle passes and all three functionalized cases stop at the reproduction's explicit missing-tangent guard. This is not a comparison against a numerically correct parent.
>
> The mechanism seems consistent with [the fresh wrapping here](https://github.com/pytorch/pytorch/blob/eb9c90dd1f2b67cadf9f7681176f1b5fab074423/torch/_subclasses/functional_tensor.py#L354-L375): mutating the returned wrapper does not update the tangent subsequently consumed by `work * 3`. [The unchanged `unpack_dual` contract](https://github.com/pytorch/pytorch/blob/eb9c90dd1f2b67cadf9f7681176f1b5fab074423/torch/autograd/forward_ad.py#L151-L158) says the tangent is returned as-is.
>
> **Evidence and limit:** [CI run and raw receipts](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36453154812), [complete reproduction](https://github.com/YS-OH-CORE/second-paddle-notes/blob/32ec7835739c728cca5d6a48c959da61aaab7832/checks/pytorch-192656-forwardad/repro.py), [source-overlay runner](https://github.com/YS-OH-CORE/second-paddle-notes/blob/32ec7835739c728cca5d6a48c959da61aaab7832/checks/pytorch-192656-forwardad/run.py). Python 3.12.3; CPU wheel binary commit `cf30153c4c131c8164ee7798e5022d810682e2cb`. Exact loaded-file hashes were checked, both variants used fresh processes over the same wheel, and original sources were restored. This is a **two-file source-overlay experiment**, not a complete build of either commit. It does not establish behavior of the separate public C++ functionalization path or an end-to-end AOTAutograd workload.
>
> Is this intermediate tangent mutation intended to remain unsupported? If so, an explicit diagnostic would make the limitation visible; otherwise, could the unpacked tangent preserve this functional dependency?
>
> — Zero × Youngseok Oh

