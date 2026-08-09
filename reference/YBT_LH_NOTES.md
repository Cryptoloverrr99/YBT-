The supplied YBT LH v2.2 source uses:
- `ta.pivothigh(high, autoPivotLeft, autoPivotRight)` and `ta.pivotlow(low, autoPivotLeft, autoPivotRight)`.
- `Pivot Left Bars`: bars required on the left side of a confirmed pivot.
- `Pivot Right Bars`: bars required on the right side and natural confirmation delay.
- `f_upsertZone()` merges same-side active zones within ATR-based distance; a merge does not create a new zone.
- A new zone is created only in the non-merge branch of `f_upsertZone()`.
- New-zone alert state is set only when `zoneCreated` is true.
- Volume boost is 3 when volume ratio > 2.5, 2 when > 1.2, otherwise 1 when volume weighting is enabled.
- Lifecycle can fade/remove a zone when price reaches it; faded score is multiplied by the fade retention factor.
