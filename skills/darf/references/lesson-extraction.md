# Lesson Extraction

DARF turns repeated or high-value review failures into reusable lessons.

## Triggers

- Gate FAIL.
- Fix cycle.
- User feedback identifies a missed issue.
- A reviewer finds a generalizable risk pattern.

## Validation

Extract a lesson only when all conditions hold:

1. Reproducible: there is specific evidence such as code, file, line, metric, or command output.
2. Non-incidental: it is not a one-off formatting or environment accident.
3. Generalizable: it can prevent a future class of failures.

## Stored Fields

- Title.
- Domain.
- Trigger scenario.
- Correct behavior.
- Wrong behavior.
- Evidence.
- Source phase.
- Frequency.

## Flow

1. Search existing lessons for similar issues.
2. Bump frequency if a matching lesson exists.
3. Otherwise add a new lesson.
4. Record the action in `execution-log.md`.
5. Sync high-frequency lessons to flat files through the configured sync command.

## Quant Examples

- Negative shift used as a feature.
- `StandardScaler.fit_transform` before chronological split.
- Random train/test split on time series.
- Gross Sharpe reported without costs.
- Unsupported state-of-the-art claim without baseline evidence.
