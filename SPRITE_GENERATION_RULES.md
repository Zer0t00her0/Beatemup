# Sprite sheet generation rules — mandatory

For all future character animation sprite sheets intended for AI Sprite Studio:

1. Use an exact regular grid. Default walk cycle: 8 columns × 1 row, with each cell identical in size. Preferred 256 × 256 px per cell, total 2048 × 256 px.
2. ONE complete character per cell. Never let a hand, boot, hair, accessory, shadow, or any part cross a cell boundary or overlap another cell.
3. Keep a safety margin of at least 10% of each cell's width and height on every side, accounting for the MOST EXTREME pose in the entire cycle. If needed, scale the entire character down uniformly rather than cropping.
4. Keep the character's pixel scale, design, silhouette, proportions, camera angle, and ground baseline consistent across frames. No arbitrary zoom or drift.
5. The walk cycle uses 8 distinct phases: contact, down, passing, up, opposite contact, opposite down, opposite passing, opposite up. Arms swing in opposition to legs; both feet take turns supporting weight.
6. Frame 8 must transition naturally to frame 1; don't duplicate frame 1 as the last frame.
7. No numbers, text labels, borders, dividers, scenery, or elements shared between cells.
8. Prefer transparent backgrounds. If unavailable, use a perfectly uniform background.
9. Validate before delivery: inspect all 8 cells independently; confirm no clipping, no neighboring sprite intrusion, and consistent foot baseline. If validation fails, regenerate or repair before describing the sheet as ready.
10. The sheet is for a strict grid slicer, so positions must be within exact, equal-width cells—not visually approximated spacing.

Short prompt clause: "Strict 8×1 sprite sheet, 8 equal 256×256 cells, one fully visible character per cell, at least 10% empty safety padding on ALL four sides in every pose, no overlap or crop, same ground baseline and scale, transparent background, eight anatomically correct walk-cycle phases with alternating legs and opposite arms."
