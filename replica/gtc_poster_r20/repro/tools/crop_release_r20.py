"""Reproduce the r20 release still: crop the rotation-fixed 4K release frame from the right only (owner request: show four
satellites, drop the partial fifth one and the empty space). Columns 0..3479 of 3840, full 1800-px height, pixels unchanged.
Usage: python tools/crop_release_r20.py [--check]   (run from repro/; --check only verifies the committed crop)"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
SRC=Path('poster_inputs/RELEASE_R11_K712_4K_CROP_fixed.png');DST=Path('poster_inputs/RELEASE_R11_K712_4K_CROP_fixed_r20right.png');W=3480
a=np.asarray(Image.open(SRC));assert a.shape[:2]==(1800,3840),a.shape
crop=a[:,:W]
if '--check' in sys.argv:
    b=np.asarray(Image.open(DST));assert b.shape==crop.shape and np.array_equal(b,crop),'committed crop differs';print('crop OK',b.shape)
else:
    Image.fromarray(crop).save(DST);print('wrote',DST,crop.shape)
