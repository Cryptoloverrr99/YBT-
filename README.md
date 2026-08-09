# Source mapping

The computational port is based on the supplied YBT LH v2.2 Pine source. Visual-only Pine objects (boxes, labels, colors, tables) are not copied into the backend. The source states that Pivot Left Bars are bars on the left of a confirmed pivot and Pivot Right Bars are bars on the right and control the natural confirmation delay. New-zone alerts are created only when `f_upsertZone()` actually creates a new zone; merges return `zoneCreated=false`.
