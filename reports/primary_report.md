# Can LLMs Audit Quant Research?

## Abstract

This project asks whether adversarial AI review can catch the methodological mistakes that quietly invalidate quantitative finance research. We integrate two locally developed adversarial-review designs, DARF and CORAX, into a reproducible benchmark that audits financial backtest code and research claims for known failure modes. Evaluating five reviewer adapters against 45 labeled cases, we find that AI-assisted review is clearly useful. It lifts recall from 0.56 for a naive rule baseline to as high as 1.00 for a live cross-model challenger, but there is no single best adapter. The two strongest configurations sit at opposite ends of a precision-recall tradeoff, and the evaluation surfaces a second, less expected result: in several cases the disagreement between reviewers points not to a reviewer error but to a genuine ambiguity in the benchmark's own labels. We treat that as a finding rather than noise.

## Motivation

AI tools can write a backtest in minutes, and that speed is exactly what makes research mistakes easier to miss. In quantitative finance, the difference between a real edge and an illusory one often lives in a single line of code. A shift in the wrong direction leaks the prediction horizon into the feature matrix. A normalization step applied before the train/test split lets test-period statistics bleed into training. A random split shuffles a time series so the model is trained on the future and tested on the past. A Sharpe ratio computed on gross returns flatters a strategy that would not survive its own transaction costs. None of these errors announces itself; each produces a backtest that looks profitable.

These are the failure modes a careful human reviewer is trained to catch. The question this project investigates is whether an AI reviewer, and specifically an *adversarial* AI reviewer, one model checking another's work, can catch them reliably enough to be worth integrating into a research workflow.

## System Designs: DARF and CORAX

The project builds on two adversarial-review designs. Both are motivated by the same observation: a model asked to review its own output tends to endorse it, because it shares the blind spots that produced the work in the first place. Both designs attack that problem, but differently.

**DARF** uses cross-model adversarial review. A producer model creates the research output. A processing step strips the producer's conclusions into a *blind brief*, that is, facts, code, and metrics with the author's judgments removed, and a separate challenger model, drawn from a different model family, reviews that brief against a phase-specific rubric. The defense against groupthink is the heterogeneity of the two models: a challenger trained differently from the producer is more likely to see what the producer missed.

**CORAX** uses a Codex-on-Codex "Santa Method" review. A Codex producer creates the work, an independent Codex instance reviews only a stripped blind brief in an isolated read-only sandbox, and a heterogeneous Claude Sentinel then inspects the exchange for same-family groupthink and shared blind spots. Because producer and reviewer are the same model family here, the Sentinel is the mechanism that compensates for the missing heterogeneity.

It is important to be precise about what this report evaluates. The descriptions above are the *complete* designs. The benchmark's live adapters exercise the core review step, a real model acting as an independent reviewer or challenger over a submitted artifact, but not the full orchestration. The blind-brief stripping stage, the Sentinel pass, and the mutation-ladder escalation are implemented in the project but are not part of the benchmarked path. The benchmark therefore measures *real-model single-pass review quality*, which is the component most directly comparable to the offline scanners, and we frame all live results accordingly.

## Benchmark Design

The benchmark contains 45 labeled audit cases. Each case is a small finance-research artifact, such as a feature-engineering snippet, a backtest, a model-training routine, a notebook workflow, or a research write-up, paired with a separate annotation recording its expected issues, severity, and a rationale.

The cases cover five failure modes plus clean controls: lookahead bias (7 cases), missing transaction costs (10), full-sample normalization leakage (7), random splits applied to time series (7), and unsupported performance claims (5), with 11 clean cases that contain no issue. The clean cases matter as much as the positive ones: they are how the benchmark detects an over-eager reviewer that flags problems where none exist. Several clean cases are deliberate near-misses, the correctly written version of a specific error, so a reviewer that confuses the two is exposed precisely.

Cases are grounded in real market data, real documents, or real finance workflows rather than synthetic fallback data. They reference a bundled BTC historical sample, a QuoteMedia multi-stock price sample, and two real tutorial notebooks. The harness raises an error when a referenced data fixture is missing and never substitutes generated data; the case loader likewise rejects missing labels, duplicate case IDs, and unknown issue types rather than passing them through silently. The intent is that the evaluation target itself is trustworthy before any reviewer is run against it.

## Methodology

Five reviewer adapters are evaluated, all through one command-line interface that loads cases, runs the selected adapter, compares its findings against the labels, and reports metrics.

Three adapters run **offline**: they reach a verdict through deterministic scans and rules, call no model, cost nothing, and return identical results on every run. `single_llm_baseline` applies a small set of regular-expression rules and serves as the naive control. `darf` and `corax` invoke the project's deterministic MCP scans for lookahead and normalization leakage.

Two adapters run **live**: `corax-live` and `darf-live` spawn a real Codex model that reads each case and produces a structured verdict. Live review is non-deterministic, since the same case can yield slightly different output across runs, and this is itself a reportable property, in contrast to the offline adapters' exact reproducibility.

Metrics are precision, recall, and F1 against the labeled issue set, alongside true/false positives, false negatives, per-run failure count, and latency. A finding is counted correct only when its issue type matches an annotated issue for that case; one case may carry more than one expected issue.

## Results

All five adapters were evaluated against the full 45-case benchmark. The live adapters completed 90 model calls with zero failures, and every case produced a parseable verdict.

| Adapter | Mode | Precision | Recall | F1 | TP | FP | FN | Failures | Latency |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single_llm_baseline | offline | 1.0000 | 0.5556 | 0.7143 | 20 | 0 | 16 | 0 | ~0s |
| darf | offline | 0.9459 | 0.9722 | 0.9589 | 35 | 2 | 1 | 0 | ~0s |
| corax | offline | 0.9459 | 0.9722 | 0.9589 | 35 | 2 | 1 | 0 | ~0s |
| corax-live | live | 0.9722 | 0.9722 | 0.9722 | 35 | 1 | 1 | 0 | 247s |
| darf-live | live | 0.8182 | 1.0000 | 0.9000 | 36 | 8 | 0 | 0 | 427s |

The results separate into three layers.

The naive baseline fails *systematically*, not randomly. Its recall of 0.56 reflects whole categories it cannot see: with no rule for full-sample normalization and no rule for unsupported claims, it misses those case types entirely. Its perfect precision is not a strength but a symptom, since it only ever fires on the few hard patterns it knows, so it never produces a false alarm because it rarely fires at all.

The offline scanners close most of that gap. Both `darf` and `corax` reach recall 0.97 by covering the categories the baseline lacks. Notably, the two are *operationally identical* on this benchmark, with the same true positives, the same false positives, and the same single false negative, because in offline mode they share the same deterministic normalization scan. The mechanism difference between DARF and CORAX does not exist offline; it only becomes visible once a real model is in the loop.

The live adapters are where DARF and CORAX diverge, and they diverge into a clear precision-recall tradeoff. `corax-live` achieves the highest F1 (0.9722), balancing precision and recall evenly. `darf-live` is the only adapter to reach recall 1.00, catching every annotated issue, but it pays for that completeness with 8 false positives, dropping its precision to 0.82. There is no single best adapter: the right choice depends on whether the review setting can better tolerate a missed problem or a false alarm.

## Case Analysis

**`cost_variable_declared_not_applied`, the case that separates live from offline.** This backtest declares a transaction-cost variable on its first line and then never subtracts it from strategy returns. The cost is present as a name but absent as an effect. Four of the five adapters, namely the baseline, both offline scanners, and `corax-live`, miss it. They miss it because detecting it requires following the data flow and noticing that a declared variable never reaches the return calculation; pattern matching sees the word "cost" and a deterministic scan has no rule for a dead store. Only `darf-live` catches it. This single case is the clearest evidence in the evaluation that a real model's semantic reading can recover an error that rule-based scanning structurally cannot, and, read the other way, it is also an honest failure case, because the majority of adapters do not catch it. It earns a place in the report as both.

**A QuoteMedia lookahead case, generalization to a new data domain.** The QuoteMedia cases use multi-stock equity data rather than the single-asset BTC sample. The live adapters detect lookahead bias correctly on these cases, confirming that the result is not an artifact of one dataset or one code style: the reviewers identify the *structure* of the error, a future return used as an input, across a data domain they were not tuned on.

**`notebook_transaction_turnover_alignment_ambiguous`, when reviewers disagree with the label.** This case is annotated clean, yet all four non-baseline adapters, both offline scanners and both live models, flag it as lookahead. The case name itself contains the word "ambiguous." When four independent reviewers, including two different model families, unanimously contradict a label, the more likely explanation is that the label sits on a genuine gray area, not that all four reviewers are wrong in the same way. We treat this as the benchmark using reviewer agreement to surface a boundary in its own annotations, and we recommend the annotation be revisited rather than counted as four separate reviewer errors.

## Where AI Helps, Where It Does Not, and Where a Human Is Needed

**Where it helps.** AI review delivers a large, real gain over naive rule checking, lifting recall from 0.56 to as high as 1.00, and the gain is concentrated exactly where rules are weakest. The `cost_variable_declared_not_applied` case shows the qualitative version of this: a live model can catch a semantic error, a declared-but-unused variable, that no deterministic scan in the benchmark detects.

**Where it does not help.** AI review does not automatically resolve the DARF-versus-CORAX design question. Offline, the two are indistinguishable on this benchmark because they share a scanner; the adversarial machinery that is supposed to differentiate them is not exercised in the offline path. The benchmark can compare detection coverage, but it cannot, in its current form, adjudicate which adversarial *design* is better.

**Where a human is needed.** The evaluation's most recurring need for human judgment is taxonomy. `darf-live`'s false positives are concentrated in a single pattern: it labels random-split cases as lookahead in addition to their annotated temporal-split issue. That overlap is defensible, since randomly splitting a time series *is* a form of forward-information leakage, so the "error" is really a disagreement about whether two labels should be distinct. Deciding that, and deciding the status of the ambiguous case above, are annotation-design choices that a human must make. The AI reviewers can expose the boundary; they cannot define it.

## Limitations

Several limitations bound these results. First, the offline DARF and CORAX adapters are operationally equivalent on this benchmark, so offline results speak to detection coverage rather than to either design's adversarial mechanism. Second, the benchmarked live path exercises single-pass model review only; the full DARF and CORAX orchestration, including blind-brief stripping, the Sentinel pass, and mutation-ladder escalation, is implemented but not evaluated here. Third, live review is non-deterministic, so individual live numbers can shift on re-runs and should be read as representative rather than exact. Fourth, the benchmark's label taxonomy has at least one contested boundary, between lookahead bias and temporal-split errors, that affects measured precision. Fifth, at 45 cases the benchmark is large enough to show clear category-level patterns but still modest for fine-grained claims about individual adapters.

## What AI Would Not Produce Alone

The central human contribution in this project is not the code that runs the reviewers but the evaluation design around them: choosing finance-specific failure modes that matter, writing labels and rationales, deciding what counts as evidence of an error, building clean controls as deliberate near-misses, and keeping reproducible benchmark results separate from claims about the adversarial designs. The evaluation itself makes the point. An AI reviewer can flag a case; it cannot decide whether its disagreement with a label means the reviewer is wrong or the label is. That judgment, and the decision to treat reviewer consensus as a signal about the benchmark rather than noise to be scored away, is the part of this work that a model would not have produced on its own.
