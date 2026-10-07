# AGENTS.md

## Project

This repository is an undergraduate research project studying
Shortest-Path Percolation (SPP) on a two-dimensional square lattice.

Working repository:

C:\Users\yoshi\graduation-research\spp-2d-lattice

Do not access, modify, inspect, or operate on any other repository,
including directed-network-simulations.

---

## Research integrity

Treat this repository as scientific research code.

Do not assume that existing documentation, implementation, tests,
CSV files, figures, previous analyses, or previous conclusions are correct
merely because they already exist in the repository.

When auditing research results, cross-check the following whenever relevant:

- mathematical/model definition
- Java implementation
- Python analysis implementation
- unit and integration tests
- small-system validation
- raw/run-level output
- condition summaries
- analysis CSV files
- generated figures
- Git history
- preregistration files
- research documentation

Always distinguish clearly between:

- facts directly established by the implementation or data
- statistical evidence
- assumptions
- interpretations
- hypotheses
- conclusions that are only consistent with the data

Do not strengthen a scientific claim beyond what the evidence supports.

---

## Audit behavior

When performing a research audit:

1. Proceed in the requested phase order.
2. Explicitly state what was checked in each phase.
3. Do not move to the next phase until the current phase is judged acceptable.
4. If a potentially conclusion-changing inconsistency is found, stop.
5. Do not silently fix the problem and continue.
6. Explain the problem, its evidence, and its possible impact.
7. Wait for the user before making any corrective change.
8. Distinguish major scientific problems from minor documentation or formatting issues.

Passing tests alone is not sufficient evidence that the scientific implementation is correct.

Documentation alone is not sufficient evidence that the code behaves as documented.

A visually plausible graph is not sufficient evidence that the underlying analysis is correct.

---

## File safety

Unless explicitly instructed otherwise, operate in audit/read-mostly mode.

Do not:

- edit source code
- edit research documentation
- modify research CSV files
- overwrite existing experiment output
- delete files
- regenerate large research datasets
- modify preregistration files
- commit
- push
- rebase
- reset
- clean
- checkout destructive changes
- rewrite Git history

Running tests is allowed.

Running lightweight analysis on existing data is allowed.

Creating temporary files for independent verification is allowed only if they
do not overwrite existing research outputs.

Do not overwrite or delete completed research data under:

app/out/

---

## Large simulation restrictions

Do not automatically rerun large simulations.

In particular, do not rerun:

- scaling-v1 main simulations
- scaling-v2 main simulations
- UNBOUNDED L=192 simulations
- UNBOUNDED L=256 simulations
- UNBOUNDED L=320 simulations
- UNBOUNDED L=384 simulations

Use existing results for auditing.

If a new large simulation appears necessary, stop and explain why before running it.

---

## Model definition

The intended research model must always be checked against the implementation.

Do not assume this section proves that the implementation is correct.

The intended model is:

- Initial graph: two-dimensional L × L square lattice
- Boundary condition: open boundary
- Graph: undirected and unweighted
- Each request selects two distinct vertices
- The requested vertex pair is selected uniformly
- Shortest paths are calculated using the currently active edges
- If the two vertices are disconnected, the request is rejected
- If the shortest-path length exceeds the budget C, the request is rejected
- Otherwise, one shortest path is selected uniformly from all shortest paths
- All edges on the selected shortest path are removed as one request event

The implementation must be audited to confirm that it actually matches this definition.

---

## Shortest-path sampling

Uniform shortest-path selection is scientifically important.

When auditing shortest-path sampling, verify:

- BFS distance computation
- shortest-path DAG construction
- shortest-path counting
- BigInteger or equivalent overflow-safe counting
- predecessor/successor probabilities
- backward or forward path sampling
- whether every complete shortest path has equal probability

Do not accept “random predecessor selection” as equivalent to uniform path
sampling unless it is mathematically justified.

---

## C = 1 as an internal benchmark

C = 1 is a critical validation condition.

Do not assume beforehand that C = 1 is ordinary bond percolation.

Instead, verify both mathematically and computationally whether:

- every accepted request removes exactly one edge
- conditional on an accepted request, every currently active edge is equally likely to be removed
- rejected requests do not bias the removed-edge ordering when removed-edge fraction p is used as the control variable
- request-level and edge-level observables coincide for C = 1
- the measured finite-size behavior is consistent with ordinary two-dimensional bond percolation

Known ordinary two-dimensional percolation values may be used only as
external validation targets after the implementation logic has been checked.

Do not force the data to agree with those values.

---

## Scientific reference values

For ordinary two-dimensional percolation, the following values may be used
as reference values in validation:

beta = 5/36

gamma = 43/18

nu = 4/3

Therefore:

beta/nu = 5/48

gamma/nu = 43/24

1/nu = 3/4

For square-lattice bond percolation:

pc = 1/2

These are comparison targets, not assumptions about SPP for arbitrary C.

Do not assume that C = 2 or UNBOUNDED must have these values.

---

## Primary and secondary observables

The primary physical event in this project is request-level deletion.

One accepted SPP request removes the entire selected shortest path as one event.

Therefore:

- request-level observables are the primary analysis
- edge-level reconstruction is a secondary analysis
- edge-level reconstruction may be used for comparison with prior literature
- edge-level quantities must not silently replace request-level quantities

When auditing results, explicitly track whether each observable is request-level or edge-level.

---

## Edge-order sensitivity

For a multi-edge shortest path, edge-level reconstruction may depend on the
artificial order in which path edges are replayed.

Therefore:

- source-to-target order
- reverse order
- shuffled order

may produce different edge-level pseudocritical behavior.

This dependence is acceptable only for the secondary edge-level analysis.

If a main scientific conclusion about SPP transition order depends on an
artificial within-path edge ordering, stop and report it.

For C = 1, request-level and edge-level results should coincide because each
accepted request removes one edge.

---

## Finite-size scaling

Finite-size scaling must be audited carefully.

Important quantities include:

- P_before
- P_after
- S_before
- S_after
- pseudocritical point
- transition width
- maximum request jump
- std(p_mid)

Important scaling forms include:

P(L, pc) ~ L^(-beta/nu)

S(L, pc) ~ L^(gamma/nu)

pc(L) - pc ~ L^(-1/nu)

When reviewing fits, check:

- which sizes are included
- L_min sensitivity
- point estimator
- bootstrap estimator
- confidence intervals
- model parameter count
- parameter bounds
- optimizer convergence
- parameter correlations
- boundary solutions
- residual structure

Do not interpret a good-looking fit alone as evidence of a correct exponent.

---

## Finite-size corrections

When correction-to-scaling models are used, verify models such as:

Y(L) = a L^x

and

Y(L) = a L^x (1 + b L^(-omega))

Check:

- free omega fits
- fixed omega fits
- lower/upper bound hits
- multi-start optimization
- parameter identifiability
- AICc and BIC calculation
- sensitivity to L_min

If omega or other correction parameters are poorly identified, do not present
the corrected exponent as precise evidence.

---

## Bootstrap and uncertainty

Bootstrap intervals must be generated using an estimator consistent with the
reported point estimator unless a difference is explicitly justified.

When auditing bootstrap results, verify:

- resampling unit
- random seed
- number of bootstrap samples
- original-scale vs log-scale fitting
- estimator consistency
- confidence interval construction

If a point estimate lies outside its reported bootstrap interval without a clear
methodological explanation, treat it as a serious inconsistency and stop.

Bootstrap uncertainty does not automatically include:

- model-form uncertainty
- finite-size systematic error
- L_min selection uncertainty
- correction-model uncertainty

Do not overstate bootstrap intervals.

---

## Universality claims

For C = 2 or other finite C values, do not assume the universality class.

The strongest acceptable wording must be determined from the actual evidence.

Possible wording may include:

“consistent with the same universality class”

or

“compatible with the same universality class”

only if supported by the fits and uncertainty analysis.

Do not automatically write:

“belongs to the same universality class”

unless the evidence is strong enough to justify that statement.

---

## Hyperscaling

When hyperscaling is used, verify that quantities from compatible definitions
are combined.

For two-dimensional systems, a common check is:

2 beta/nu + gamma/nu = 2

Do not mix before-event and after-event estimates in one hyperscaling relation
unless that choice is explicitly justified.

---

## UNBOUNDED transition analysis

For UNBOUNDED, finite-size abruptness alone is not sufficient evidence of a
discontinuous transition.

The main asymptotic question is whether the maximum request jump tends to zero
or a finite positive limit.

Relevant model families include:

zero-power

Y(L) = a L^(-x)

finite-power

Y(L) = Y_inf + a L^(-x)

zero-log

Y(L) = a (log L)^(-x)

finite-log

Y(L) = Y_inf + a (log L)^(-x)

When comparing these models, verify:

- fitted parameters
- parameter bounds
- boundary fits
- AICc
- BIC
- leave-one-out metrics
- sequential prediction
- bootstrap behavior
- parameter correlations
- preregistered predictions

Do not equate an abrupt finite-size curve with a true discontinuity in the
thermodynamic limit.

---

## Preregistration integrity

For L = 320 and L = 384 preregistered analyses, verify:

- preregistration file contents
- Git history
- commit order
- whether predictions existed before the corresponding simulation results
- whether preregistration files were modified after results were available

If preregistration appears to have been altered after observing results, stop
and report it.

Do not modify preregistration files during an audit.

---

## Numerical sanity checks

When inspecting simulation output, check for obvious numerical or logical anomalies.

Examples:

- P outside [0, 1]
- removed-edge fraction p outside [0, 1]
- impossible cluster sizes
- non-monotonic removed-edge counts
- duplicate seeds
- missing runs
- duplicated runs
- inconsistent manifest counts
- impossible accepted/rejected totals
- unexpected stop reasons
- NaN or infinite values
- discontinuities caused by output or indexing bugs
- before/after values reversed

Do not discard outliers without explaining them.

---

## Reproducibility

When relevant, verify:

- deterministic behavior for fixed seeds
- separation of RNG streams
- manifest completeness
- resume behavior
- shard completeness
- stop-audit independence
- preregistration protection
- analysis input provenance

Do not regenerate completed datasets merely to prove reproducibility.

---

## Documentation consistency

Research documents must be compared with the actual implementation and output.

Older documents may represent historical states and should not automatically be
treated as current truth.

When documentation and implementation disagree:

1. identify which version each describes
2. determine whether the disagreement is historical or an actual inconsistency
3. do not silently rewrite the documentation during the audit

---

## Git behavior

Git may be used for read-only inspection.

Allowed examples:

- git status
- git log
- git show
- git diff
- git branch
- git rev-parse

Do not perform destructive or history-changing Git operations.

Do not commit or push unless explicitly instructed after the audit.

---

## Testing

Tests may be executed when useful.

Typical commands include:

.\gradlew.bat test

.\gradlew.bat build

python -m pytest analysis/tests

A successful test suite is evidence, but not proof, of scientific correctness.

Also inspect whether tests actually validate the intended scientific model.

---

## Audit stopping rule

Stop immediately if any issue is found that could materially change:

- the model definition
- C = 1 validation
- estimated critical exponents
- pseudocritical scaling
- universality conclusions
- transition-order conclusions
- UNBOUNDED asymptotic conclusions
- preregistration integrity

When stopping, report:

- what is wrong
- where it occurs
- the evidence
- expected behavior
- observed behavior
- likely causes
- possible impact
- what should be checked next

Do not fix it automatically.

---

## Communication style

When reporting scientific audit results:

- be precise
- distinguish evidence from interpretation
- include file paths and function names
- include numerical values when relevant
- explain mathematical reasoning in plain language
- avoid vague statements such as “looks fine”
- explicitly say why a phase passes or fails

If uncertainty remains, state it clearly instead of forcing a conclusion.