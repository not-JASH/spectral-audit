# Novelty audit — initial note

Welch's 1967 modified-periodogram method, its averaging over windowed segments,
and window-energy normalization are established methods [W1967]. SciPy documents
the production `welch` API's density versus spectrum scaling, one-sided folding,
segment detrending, and mean averaging [SCIPY-WELCH]. SciPy's Hann API distinguishes
the default symmetric window from the periodic spectral-analysis window
[SCIPY-HANN]. This increment implements and independently checks that known
normalization; it makes no novelty claim for Welch or its Parseval accounting.

The prospective research question concerns whether explicit measurement contracts
and later diagnostics help identify misleading comparisons between distinct
finite-record and population quantities. No diagnostic evaluation or research
conclusion has been completed. The broader nearest-work review remains an M1 task.

[W1967]: https://doi.org/10.1109/TAU.1967.1161901
[SCIPY-WELCH]: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
[SCIPY-HANN]: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.hann.html
