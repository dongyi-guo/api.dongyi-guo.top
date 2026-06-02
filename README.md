# api.dongyi-guo.top

Dynamic flat JSON API hub.

## Store format

`api_store.json` is intentionally server-local. It must be valid JSON shaped as:

```json
{
  "value": {
    "value": 42
  }
}
```

The top-level key is the public handle, so this example serves `GET /value` and `POST /value`.
Each handle value must be one flat object of key/value pairs. Nested objects and arrays are rejected.

If the admin UI reports that `api_store.json` cannot be loaded, unlock with the admin token and use **Reset store**. The reset action backs up the broken file before writing the default `/value` handle.
