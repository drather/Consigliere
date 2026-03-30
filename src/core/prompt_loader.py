import yaml
from jinja2 import Template
from typing import Dict, Any, Tuple
from .storage.base import StorageProvider

class PromptLoader:
    """
    Loads and renders prompts from storage.
    Supports YAML Frontmatter for metadata and Jinja2 for templating.
    """

    def __init__(self, storage: StorageProvider, base_dir: str = "src/prompts"):
        self.storage = storage
        self.base_dir = base_dir

    def load(self, prompt_path: str, variables: Dict[str, Any] = None) -> Tuple[Dict[str, Any], str]:
        """
        Loads a prompt file and returns (metadata, rendered_content).

        Args:
            prompt_path: Path relative to base_dir (e.g., 'system/consigliere.md')
            variables: Dictionary of variables to inject into the template.

        Returns:
            Tuple containing metadata (dict) and the final prompt string.
        """
        full_path = f"{self.base_dir}/{prompt_path}"
        if not full_path.endswith(".md"):
            full_path += ".md"

        raw_content = self.storage.read_file(full_path)
        metadata, body = self._parse_frontmatter(raw_content)

        # Render Jinja2 template
        template = Template(body)
        rendered_content = template.render(variables or {})

        return metadata, rendered_content

    def load_with_cache_split(
        self,
        prompt_path: str,
        variables: Dict[str, Any] = None,
    ) -> Tuple[Dict[str, Any], str, str]:
        """
        Loads and renders a prompt, then splits it into static and dynamic parts.

        Uses the ``cache_boundary`` key in YAML frontmatter as the split point.
        The static part (before the boundary) is suitable for Claude prompt caching.
        The dynamic part (from the boundary onwards) changes per request.

        Returns:
            Tuple of (metadata, static_text, dynamic_text).
            If no ``cache_boundary`` is set, static_text = full rendered prompt, dynamic_text = "".
        """
        metadata, rendered = self.load(prompt_path, variables=variables)
        boundary = metadata.get("cache_boundary", "")
        if boundary and boundary in rendered:
            idx = rendered.index(boundary)
            return metadata, rendered[:idx].strip(), rendered[idx:].strip()
        return metadata, rendered, ""

    def _parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Splits the content into YAML metadata and Markdown body."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                    return metadata, body
                except yaml.YAMLError:
                    pass
        return {}, content.strip()
