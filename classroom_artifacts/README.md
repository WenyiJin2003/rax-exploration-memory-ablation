# Classroom experiment bundle

This folder contains the 24 held-out test animations and the exact source files used in the comparison.

Each GIF shows the three compiled controllers in the same held-out world:

- **Gray:** zero-shot controller
- **Blue:** exploration controller
- **Purple:** exploration + memory controller

## 24 held-out test GIFs

| Test | Seed | Animation | Test | Seed | Animation |
|---:|---:|---|---:|---:|---|
| 01 | 201 | [Open GIF](heldout_gifs/test_01_seed_201.gif) | 13 | 213 | [Open GIF](heldout_gifs/test_13_seed_213.gif) |
| 02 | 202 | [Open GIF](heldout_gifs/test_02_seed_202.gif) | 14 | 214 | [Open GIF](heldout_gifs/test_14_seed_214.gif) |
| 03 | 203 | [Open GIF](heldout_gifs/test_03_seed_203.gif) | 15 | 215 | [Open GIF](heldout_gifs/test_15_seed_215.gif) |
| 04 | 204 | [Open GIF](heldout_gifs/test_04_seed_204.gif) | 16 | 216 | [Open GIF](heldout_gifs/test_16_seed_216.gif) |
| 05 | 205 | [Open GIF](heldout_gifs/test_05_seed_205.gif) | 17 | 217 | [Open GIF](heldout_gifs/test_17_seed_217.gif) |
| 06 | 206 | [Open GIF](heldout_gifs/test_06_seed_206.gif) | 18 | 218 | [Open GIF](heldout_gifs/test_18_seed_218.gif) |
| 07 | 207 | [Open GIF](heldout_gifs/test_07_seed_207.gif) | 19 | 219 | [Open GIF](heldout_gifs/test_19_seed_219.gif) |
| 08 | 208 | [Open GIF](heldout_gifs/test_08_seed_208.gif) | 20 | 220 | [Open GIF](heldout_gifs/test_20_seed_220.gif) |
| 09 | 209 | [Open GIF](heldout_gifs/test_09_seed_209.gif) | 21 | 221 | [Open GIF](heldout_gifs/test_21_seed_221.gif) |
| 10 | 210 | [Open GIF](heldout_gifs/test_10_seed_210.gif) | 22 | 222 | [Open GIF](heldout_gifs/test_22_seed_222.gif) |
| 11 | 211 | [Open GIF](heldout_gifs/test_11_seed_211.gif) | 23 | 223 | [Open GIF](heldout_gifs/test_23_seed_223.gif) |
| 12 | 212 | [Open GIF](heldout_gifs/test_12_seed_212.gif) | 24 | 224 | [Open GIF](heldout_gifs/test_24_seed_224.gif) |

Test 22 / seed 222 is the clearest failure case: the zero-shot controller does not reach the goal, while both explored controllers succeed without contact.

## Memory and controllers

- [Zero-shot controller](source_files/zero_shot_controller.py)
- [Exploration controller](source_files/exploration_controller.py)
- [Exploration + memory controller](source_files/exploration_memory_controller.py)
- [Persistent memory file](source_files/memory.md)

These are copied from the original run directories without modification so the classroom bundle can be opened by itself.

## Regenerate the GIFs

From the repository root:

```bash
python3 scripts/render_all_heldout_gifs.py
```

The renderer reads the original `heldout_results.json` files and writes the animations to `classroom_artifacts/heldout_gifs/`.
