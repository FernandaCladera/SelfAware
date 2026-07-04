Attempt {attempt_n}: your previous driver for this device FAILED. Repair it.

{spec_block}

Your previous code:

```python
{previous_code}
```

Failure kind: {failure_kind}

the board replied:

```
{verbatim_error}
```

Read the error literally — it names the exact line and cause. Fix THAT, keep
everything that already worked, and restate in `reasoning` what the error
implied and what you changed. Same contract: `class Driver`, no-arg
constructor, {method_contract}.
