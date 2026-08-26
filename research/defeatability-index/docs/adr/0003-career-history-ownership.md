# Keep study-specific career history downstream

Status: accepted

`toronto-election-results` owns persistent Person identity and completed election results within
its declared coverage, while `defeatability-index` owns the supplemental career history needed for
the challenger-history study. External Candidacies and Office tenures are keyed to upstream Person
IDs; any identity correction is made upstream, and this project never creates a competing Person
registry. This keeps study-specific pre-2003 and otherwise out-of-scope research from expanding the
upstream dataset into a general political-biography database, at the accepted cost of maintaining a
sourced downstream supplement.
