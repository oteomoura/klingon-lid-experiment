# Pointer Manifests (No Text)

Each line is a JSON object like:

```json
{"lang":"pt","dump":"20231101.pt","page_id":"12345","rev_id":null,"char_start":0,"char_end":800,"sha256_expected":null}
```

- `dump` — dated Wikipedia snapshot (immutable).
- `page_id` — page identifier in that dump.
- `rev_id` — optional exact revision id if available.
- `char_start`, `char_end` — character offsets for the snippet.
- `sha256_expected` — optional integrity hash of the selected snippet.
