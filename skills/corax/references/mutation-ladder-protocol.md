# Mutation Ladder Protocol

The mutation ladder is used when normal fix cycles do not resolve reviewer/Sentinel concerns or when Sentinel flags high groupthink.

## Axes

1. Persona: change producer or reviewer role.
2. Context composition: change supporting evidence and lesson reminders.
3. Constraint injection: add hard prohibitions or required checks.
4. Adversarial framing: require the model to search for likely failures.
5. Diversity requirement: force multiple candidate solutions before choosing.
6. Failure scenario priming: inject similar past failures.
7. Sampling: generate alternatives before final selection.
8. Reference anchoring: require citations to evidence or lessons.

## Rounds

- Round 1: apply three axes.
- Round 2: apply five axes.
- Round 3: apply all eight axes.

If groupthink remains high after Round 3, escalate to the user.

## Output

Every mutation round should record:

- Trigger.
- Axes selected.
- Prompt changes.
- Resulting verdict.
- Whether the concern was resolved.
