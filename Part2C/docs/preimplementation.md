# Implementation decisions

These decisions describe the supplied implementation. They are not evidence of candidate review.

## Resolutions

* One application gateway implements dispatch, receipts and narrow reviewer reads. Profiles
  have separate source and recipient ACLs; recipient must also be allowed to see every cited ID.
* Exactly four independent scripted adapters; ORCH, comparator, assembler and gates are code.
  In-process capability isolation is appropriate only for these supplied scripts, not hostile Python.
* Release-owned expected hashes are literals in source metadata, independent of annex files;
  runtime never regenerates expectations. Joint source/release compromise remains out of scope.
* Local human role uses an OS username allowlist in trusted local configuration, explicit terminal
  action and substantive rationale. This is not enterprise authentication.
* Known: exact equality of abstract feature sets to a sample signature; variation: nonempty
  intersection with a signature; new: nonempty supported features without intersection; otherwise
  abstain. Features are modelling assumptions, never facts about real people.
* One card per supported scenario is below the three-card cap. Four rounds are available;
  default scripts use two rounds. No-pattern is explicit for S5/insufficient evidence.
* CF reruns start from annex baseline and empty history. No parent messages are copied;
  therefore removed-actor messages and their descendants cannot leak. New contributions can
  independently form. Findings compare validated contribution graphs, not actor counts alone.
* Every participating role in multi-party cards needs a completed, decisive CF. Failed,
  inconclusive or capped CF blocks human eligibility. A surviving two-role pattern does not
  establish single-actor feasibility.
* Candidate-linked evaluation checks the actual transcript and card in Phase 4. Phase 6 is a
  separate bounded TEST suite; no test approval mutation is permitted. Approval concurrency
  tests use synthetic CANDIDATE databases outside the evaluation harness.
* Schema failures allow two repairs with immutable scope; policy/content failures never retry.
  Time/call/turn/round limits stop before the next operation; interrupted RUNNING records become
  INCOMPLETE on explicit recovery, never silently resumed or approved.
* Human rejection of a material recorded step appends an annotation and moves pending cards
  to REVISION_REQUESTED. Trace rows stay unchanged; acceptance never approves a card.

