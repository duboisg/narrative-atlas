# mars-trilogy-poc

## UNDERHILL / SHIFT 1 (web POC)

Crude, deterministic prototype for testing **movement-as-commitment + time pressure + proximity dialogue**.

### Run

From the repo root:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080` and play with **WASD / arrow keys**.

### Notes

- **No pause / no save**: the clock runs continuously until the directive arrives.
- **Interaction**: stand **next to** a character to trigger dialogue; press **1 / 2 / 3** to respond.
- **Walking away** mid-conversation has consequences.
- For quick iteration you can shorten a run with `?t=120` (2 minutes), e.g. `http://localhost:8080/?t=120`.