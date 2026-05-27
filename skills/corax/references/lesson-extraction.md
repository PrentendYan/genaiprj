# CORAX Lesson Extraction

CORAX writes reusable lessons when review failures reveal generalizable risks.

## Triggers

- Reviewer FAIL.
- Sentinel soft or hard veto.
- Mutation ladder activation.
- Fix cycle.
- User feedback about a missed issue.

## Validation

All three conditions must hold:

1. Reproducible: specific evidence exists.
2. Non-incidental: not a one-off environment or formatting issue.
3. Generalizable: useful for future reviews.

## Shared DB Contract

CORAX writes lessons with `source_framework='corax'`. Framework-specific fields go into `metadata`. Search can filter by `source_framework` with `None` or `corax`.

## Domain Mapping

If an existing DB preserves legacy domain constraints, map CORAX categories into allowed domains while preserving the original CORAX category in metadata.

Example:

```json
{
  "domain": "gate_rubric",
  "metadata": {
    "corax_category": "sentinel_groupthink"
  },
  "source_framework": "corax"
}
```

## Sync

High-frequency lessons may be synced to flat files under the configured lessons-flat directory. Do not write ad hoc lesson files outside the configured sync path.
