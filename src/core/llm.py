import os
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import json

class LLMClient:
    """
    Wrapper for Google Gemini API.
    Handles prompt execution and structured output parsing.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ WARNING: GEMINI_API_KEY not found. LLM features will fail.")
        else:
            genai.configure(api_key=self.api_key)
            # Using Gemini 3 Flash for efficiency and better quota availability
            self.model = genai.GenerativeModel('gemini-3-flash-preview')

    def generate(self, prompt: str) -> str:
        """Generates raw text response."""
        if not self.api_key:
            return "[Error: Missing API Key]"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return str(e)

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generates JSON response by enforcing JSON mode or parsing text.
        """
        if not self.api_key:
            return {"error": "Missing API Key"}

        try:
            # We can use 'response_mime_type' for newer models, 
            # but for broad compatibility, we ask for JSON in prompt and parse it.
            # Or use `generation_config={"response_mime_type": "application/json"}`
            
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ LLM JSON Error: {e}")
            # Fallback: try to find JSON block in text
            try:
                import re
                match = re.search(r"\{.*\}", str(e), re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except:
                pass
            return {"error": str(e)}
