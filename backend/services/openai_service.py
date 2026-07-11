"""
IndiaPix Metadata Automation System — OpenAI GPT-4o Integration Service
Handles communication with OpenAI's GPT-4o API for metadata generation.
"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import List

from openai import OpenAI

from config import settings
from models.metadata import MetadataResult, KeywordCategories
from prompts.master_prompt import MASTER_PROMPT

logger = logging.getLogger(__name__)


class OpenAIAPIError(Exception):
    """Raised when OpenAI API returns an error or unexpected response."""
    pass


def _encode_image(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_client() -> OpenAI:
    """Get or create the OpenAI client."""
    api_key = settings.openai_api_key
    if not api_key:
        raise OpenAIAPIError(
            "OpenAI API key not configured. "
            "Set OPENAI_API_KEY in the .env file."
        )
    return OpenAI(api_key=api_key)


def _parse_response(raw_text: str) -> dict:
    """
    Parse OpenAI's JSON response, handling markdown code blocks if present.
    
    Args:
        raw_text: Raw text response from OpenAI API.
    
    Returns:
        Parsed JSON dictionary.
    
    Raises:
        OpenAIAPIError: If parsing fails.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                start_idx = i + 1
                break
        end_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        text = "\n".join(lines[start_idx:end_idx]).strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise OpenAIAPIError(
            f"Failed to parse OpenAI response as JSON: {e}\n"
            f"Raw text: {raw_text[:500]}"
        )


def _validate_and_build_metadata(data: dict) -> MetadataResult:
    """
    Validate the OpenAI response data and build a MetadataResult.
    
    Ensures all required fields are present and within spec limits.
    """
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
        raise OpenAIAPIError(f"Metadata validation failed: {e}")


def generate_metadata(
    frame_paths: List[str],
    description: str = "",
    max_retries: int = 2,
) -> MetadataResult:
    """
    Send frames to OpenAI GPT-4o API and return parsed metadata.
    
    Args:
        frame_paths: List of paths to extracted frame images.
        description: Optional operator description/context.
        max_retries: Number of retry attempts on failure.
    
    Returns:
        MetadataResult with title, caption, description, keywords, etc.
    
    Raises:
        OpenAIAPIError: If API call fails after all retries.
    """
    client = _get_client()
    
    if len(frame_paths) > settings.openai_max_images:
        raise OpenAIAPIError(
            f"Cannot send {len(frame_paths)} frames. "
            f"Maximum is {settings.openai_max_images} per request."
        )
    if len(frame_paths) == 0:
        raise OpenAIAPIError("No frames to process.")
    
    # Build the message content
    content = []
    
    # Add images
    for frame_path in frame_paths:
        try:
            encoded = _encode_image(frame_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded}",
                    "detail": "low",
                },
            })
        except Exception as e:
            logger.warning(f"Failed to encode frame {frame_path}: {e}")
            continue
    
    if not content:
        raise OpenAIAPIError("No frames could be encoded for API request.")
    
    # Add the master prompt
    prompt = MASTER_PROMPT.format(
        description=description or "None provided"
    )
    content.append({"type": "text", "text": prompt})
    
    # Send to OpenAI with retry logic
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            logger.info(
                f"Sending {len(frame_paths)} frames to OpenAI GPT-4o "
                f"(attempt {attempt + 1}/{max_retries + 1})"
            )
            
            start_time = time.monotonic()
            response = client.chat.completions.create(
                model=settings.openai_model,
                max_tokens=settings.openai_max_tokens,
                messages=[{"role": "user", "content": content}],
            )
            elapsed = time.monotonic() - start_time
            
            raw_text = response.choices[0].message.content or ""
            
            if not raw_text:
                raise OpenAIAPIError("OpenAI returned empty response")
            
            # Log latency and token usage
            token_usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                token_usage = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage, "completion_tokens", 0),
                    "total_tokens": getattr(usage, "total_tokens", 0),
                }
            
            logger.info(
                f"OpenAI API response received in {elapsed:.2f}s. "
                f"Tokens: {token_usage}",
                extra={
                    "api_provider": "openai",
                    "api_elapsed_seconds": round(elapsed, 3),
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                    "frames_sent": len(frame_paths),
                },
            )
            
            data = _parse_response(raw_text)
            metadata = _validate_and_build_metadata(data)
            
            logger.info(
                f"Successfully generated metadata for {len(frame_paths)} frames. "
                f"Title: {metadata.title[:50]}..."
            )
            return metadata
            
        except OpenAIAPIError as e:
            last_error = e
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2
                logger.warning(f"Error. Retrying in {wait_time}s... {e}")
                time.sleep(wait_time)
                continue
        except Exception as e:
            last_error = OpenAIAPIError(f"OpenAI API error: {e}")
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2
                logger.warning(f"API error. Retrying in {wait_time}s... {e}")
                time.sleep(wait_time)
                continue
            break
    
    raise last_error or OpenAIAPIError("Metadata generation failed after all retries")
