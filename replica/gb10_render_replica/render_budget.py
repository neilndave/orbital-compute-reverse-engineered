#!/usr/bin/env python3
"""Sizes RENDER 1 (Aug fleet, 30 sats, 816 frames) and RENDER 2 (one Jun + one Aug satellite, 476 frames each; frames 340..815) and the schedule.
  render_budget.py prior                                   -> PRIOR from the old clip (816 fr, 1080p, 256 spp, 33.2 s/frame, 14 sats): ESTIMATE, assumed 10 s fixed per frame + 23.2 s pixel work
  render_budget.py R1_t16 R1_t32 R2_t16 R2_t32             -> MEASURED: preview s/frame at 960x540 with 16 and 32 spp (same frames; run_preview_render.sh does both), R1 = Aug fleet, R2 = one satellite
Model: s/frame = fixed + k * pixels * spp  (k from the two preview spp points).  Deadline: last compute Fri Nov 6 5 PM PT = Sat Nov 7 9 AM Taipei; 1.5x safety on the sum."""
import sys, datetime as dt
if sys.argv[1] == "prior":
    k1 = 23.2 * 1.3 / (1920 * 1080 * 256); fx1 = 10 * 30 / 14.0       # R1: 30 sats vs 14 (fixed per-frame pose/instancer update scales with count), geometry factor 1.3 on pixel work
    k2 = 23.2 * 0.6 / (1920 * 1080 * 256); fx2 = 3.0                    # R2: single satellite, fixed ~3 s, pixel work 0.6x (smaller geometry, same sky/earth)
else:
    a1, b1, a2, b2 = map(float, sys.argv[1:5]); P = 960 * 540
    k1 = (b1 - a1) / (P * 16); fx1 = a1 - k1 * P * 16; k2 = (b2 - a2) / (P * 16); fx2 = a2 - k2 * P * 16
    print(f"measured: R1 fixed {fx1:.1f} s, R2 fixed {fx2:.1f} s")
def t(k, fx, W, H, spp): return fx + k * W * H * spp
print("hours (R1 = 816 fr; R2 = 2 x 476 fr), x1.5 safety, and the latest start of R1 (R2 follows) to finish by Sat Nov 7 9 AM Taipei:")
for (W, H, spp) in ((1280, 720, 64), (1280, 720, 128), (1280, 720, 192), (1280, 720, 256), (1920, 1080, 128)):
    s1 = t(k1, fx1, W, H, spp); s2 = t(k2, fx2, W, H, spp); h1 = 816 * s1 / 3600; h2 = 2 * 476 * s2 / 3600; tot = (h1 + h2) * 1.5
    last = dt.datetime(2026, 11, 7, 9, 0) - dt.timedelta(hours=tot)
    print(f"  {W}x{H} {spp:4d} spp: R1 {s1:5.1f} s/fr = {h1:5.1f} h | R2 {s2:5.1f} s/fr = {h2:4.1f} h | both x1.5 = {tot:5.1f} h | latest R1 start {last:%a %b %d %H:%M} Taipei = {last - dt.timedelta(hours=16):%a %b %d %H:%M} PT")
