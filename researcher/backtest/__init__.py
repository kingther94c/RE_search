"""Walk-forward valuation backtest — the precondition for every ACCEPT/REJECT verdict.

The mandate calls time-consistent out-of-sample pseudo-valuation *mandatory*; nothing
here fabricates it. Pipeline:

    store   = TransactionStore.load()        # normalized URA caveats (as-of queryable)
    subjects= store.subjects(...)            # transactions to re-price out-of-sample
    result  = walk_forward(store, subjects, METHODS)   # each subject valued as of the
                                             # end of the month BEFORE its caveat month,
                                             # seeing only caveats lodged by then.
    result.summary()                         # MAE, median/P90 APE, coverage, bias, ...

A method only earns a place in a skill if it beats the simple benchmarks in `benchmarks`
on this harness. See research/registry/ for the experiment log and method graveyard.
"""
