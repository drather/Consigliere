# Real Estate Monitor Issues Log

## ⚠️ API Key Missing
- **Symptom:** `MOLIT_API_KEY` not found in `.env`.
- **Impact:** Real API calls will fail, returning `None`.
- **Workaround:** Unit tests use `MagicMock` to simulate API responses.
- **Solution:** User must add the key to `.env` file manually.

## 🚫 401 Unauthorized (Service Key Error)
- **Symptom:** API returns `401 Unauthorized` or `<resultCode>99</resultCode>`.
- **Root Cause:**
  1. **Key Format:** data.go.kr now issues **Hex keys** (e.g., `87c0...`) which do NOT require Base64 decoding, unlike older keys (`...==`).
  2. **Double Encoding:** `requests` library automatically URL-encodes parameters. If you manually encode the key before passing it, it gets double-encoded.
- **Solution:**
  - Use the **Hex Key** directly in `.env`.
  - Pass the key as a raw string in `requests.get(params={'serviceKey': key})`.
  - Do NOT manually construct the URL query string.
