# 🤖 AI Integration Troubleshooting
Issues related to Gemini API, LLM Models, Prompts, and Quotas.

## 💎 Gemini API
### Issue: Gemini API Quota Exceeded (`429 Resource Exhausted`)
- **Date:** 2026-02-15
- **Symptom:** AI features fail with `429 Quota exceeded` error.
- **Root Cause:** The `gemini-3-pro-preview` model has strict quotas or billing requirements on the API key being used.
- **Solution:**
  1. Switch to a more efficient model: `gemini-3-flash-preview`.
  2. Check Google AI Studio billing settings.
