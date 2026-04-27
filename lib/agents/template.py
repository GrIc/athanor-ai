from pathlib import Path
from typing import Optional

def render_system_prompt(project_name: str, checkpoint: Optional[str] = None, hint: Optional[str] = None) -> str:
    """Build system prompt from generic template + project-specific context."""
    template_path = Path("agents/defs/default.md")

    if template_path.exists():
        template_content = template_path.read_text(encoding="utf-8")
    else:
        # Fallback if file doesn't exist
        template_content = (
            "You are an assistant specialized in the {project_name} project.\n"
            "You have access to all indexed documents for this project.\n"
            "{checkpoint_context}\n"
            "Always cite your sources (filename + excerpt) when answering.\n"
            "{user_hint}"
        )

    checkpoint_context = f"\n## Current project state\n{checkpoint}\n" if checkpoint else ""
    user_hint = f"\n{hint}\n" if hint else ""

    return template_content.format(
        project_name=project_name,
        checkpoint_context=checkpoint_context,
        user_hint=user_hint
    )