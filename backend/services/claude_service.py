"""
IndiaPix Metadata Automation System — Claude API Integration Service
Handles communication with Anthropic's Claude API for metadata generation.
"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import List, Optional

import anthropic

from config import settings
from models.metadata import MetadataResult, KeywordCategories
from prompts.master_prompt import MASTER_PROMPT

logger = logging.getLogger(__name__)


class ClaudeAPIError(Exception):
    """Raised when Claude API returns an error or unexpected response."""
    pass


def _encode_image(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_client() -> anthropic.Anthropic:
    """Get or create the Anthropic client."""
    api_key = settings.anthropic_api_key
    if not api_key or api_key == "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
        raise ClaudeAPIError(
            "Anthropic API key not configured. "
            "Set ANTHROPIC_API_KEY in the .env file."
        )
    return anthropic.Anthropic(api_key=api_key)


def _parse_claude_response(raw_text: str) -> dict:
    """
    Parse Claude's JSON response, handling markdown code blocks if present.
    
    Args:
        raw_text: Raw text response from Claude API.
    
    Returns:
        Parsed JSON dictionary.
    
    Raises:
        ClaudeAPIError: If parsing fails.
    """
    # Strip markdown code blocks if present
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove opening ```json or ``` and closing ```
        lines = text.split("\n")
        # Find first code fence and remove it
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                start_idx = i + 1
                break
        # Find closing code fence
        end_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        text = "\n".join(lines[start_idx:end_idx]).strip()
    
    # Parse JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ClaudeAPIError(
            f"Failed to parse Claude response as JSON: {e}\n"
            f"Raw text: {raw_text[:500]}"
        )


def _validate_and_build_metadata(data: dict) -> MetadataResult:
    """
    Validate the Claude response data and build a MetadataResult.
    
    Ensures all required fields are present and within spec limits.
    """
    # Extract keywordCategories if present
    kw_categories = KeywordCategories()
    raw_cats = data.get("keywordCategories", {})
    if raw_cats:
        kw_categories = KeywordCategories(
            people=raw_cats.get("people", []),
            action=raw_cats.get("action", []),
            location=raw_cats.get("location", []),
            setting=raw_cats.get("setting", []),
            technical=raw_cats.get("technical", []),
            conceptual=raw_cats.get("conceptual", []),
        )
    
    # Build metadata result
    # Note: 'title' in MetadataResult now stores what the AI returns as 'caption'
    # The old separate 'title' field has been removed. We use caption as the main headline.
    try:
        title_value = data.get("caption") or data.get("title", "Untitled")
        metadata = MetadataResult(
            title=title_value[:200],
            description=data.get("description", "")[:500],
            keywords=data.get("keywords", [])[:50],
            category=data.get("category", ""),
            location=data.get("location", "Unknown"),
            mood=data.get("mood", ""),
            shotType=data.get("shotType", ""),
            editorial=bool(data.get("editorial", False)),
            keywordCategories=kw_categories,
        )
        return metadata
    except Exception as e:
        raise ClaudeAPIError(f"Metadata validation failed: {e}")


def generate_metadata(
    frame_paths: List[str],
    description: str = "",
    max_retries: int = 2,
) -> MetadataResult:
    """
    Send frames to Claude API and return parsed metadata.
    
    Args:
        frame_paths: List of paths to extracted frame images.
        description: Optional operator description/context.
        max_retries: Number of retry attempts on failure.
    
    Returns:
        MetadataResult with title, caption, description, keywords, etc.
    
    Raises:
        ClaudeAPIError: If API call fails after all retries.
    """
    client = _get_client()
    
    # Validate frame count
    if len(frame_paths) > settings.claude_max_images:
        raise ClaudeAPIError(
            f"Cannot send {len(frame_paths)} frames. "
            f"Maximum is {settings.claude_max_images} per request."
        )
    if len(frame_paths) == 0:
        raise ClaudeAPIError("No frames to process.")
    
    # Build the message content
    content = []
    
    # Add images
    for frame_path in frame_paths:
        try:
            encoded = _encode_image(frame_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encoded,
                },
            })
        except Exception as e:
            logger.warning(f"Failed to encode frame {frame_path}: {e}")
            continue
    
    if not content:
        raise ClaudeAPIError("No frames could be encoded for API request.")
    
    # Add the master prompt
    prompt = MASTER_PROMPT.format(
        description=description or "None provided"
    )
    content.append({"type": "text", "text": prompt})
    
    # Send to Claude with retry logic
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Sending {len(frame_paths)} frames to Claude API "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )
            
            start_time = time.monotonic()
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                messages=[{"role": "user", "content": content}],
            )
            elapsed = time.monotonic() - start_time
            
            # Extract response text
            raw_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw_text += block.text
            
            if not raw_text:
                raise ClaudeAPIError("Claude returned empty response")
            
            # Log latency and token usage
            token_usage = {}
            if hasattr(response, "usage"):
                usage = response.usage
                token_usage = {
                    "input_tokens": getattr(usage, "input_tokens", 0),
                    "output_tokens": getattr(usage, "output_tokens", 0),
                }
            
            logger.info(
                f"Claude API response received in {elapsed:.2f}s. "
                f"Tokens: {token_usage}",
                extra={
                    "api_provider": "claude",
                    "api_elapsed_seconds": round(elapsed, 3),
                    "input_tokens": token_usage.get("input_tokens", 0),
                    "output_tokens": token_usage.get("output_tokens", 0),
                    "frames_sent": len(frame_paths),
                },
            )
            
            # Parse and validate
            data = _parse_claude_response(raw_text)
            metadata = _validate_and_build_metadata(data)
            
            logger.info(
                f"Successfully generated metadata for {len(frame_paths)} frames. "
                f"Title: {metadata.title[:50]}..."
            )
            return metadata
            
        except anthropic.RateLimitError as e:
            last_error = ClaudeAPIError(f"Claude API rate limit exceeded: {e}")
            if attempt < max_retries:
                wait_time = (attempt + 1) * 5  # Progressive backoff
                logger.warning(f"Rate limited. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
        except anthropic.APIError as e:
            last_error = ClaudeAPIError(f"Claude API error: {e}")
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2
                logger.warning(f"API error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
        except (ClaudeAPIError, Exception) as e:
            last_error = ClaudeAPIError(f"Metadata generation failed: {e}")
            if attempt < max_retries:
                logger.warning(f"Error. Retrying... {e}")
                continue
            break
    
    raise last_error or ClaudeAPIError("Metadata generation failed after all retries")
