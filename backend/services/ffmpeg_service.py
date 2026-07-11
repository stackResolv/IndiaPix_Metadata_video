"""
IndiaPix Metadata Automation System — FFmpeg Frame Extraction Service
Handles video duration detection, frame count calculation, and frame extraction.
Also provides comprehensive video property extraction via ffprobe.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import settings

logger = logging.getLogger(__name__)


def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds using ffprobe.
    
    Args:
        video_path: Path to the video file.
    
    Returns:
        Duration in seconds as a float.
    
    Raises:
        RuntimeError: If ffprobe fails or duration cannot be determined.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed (exit code {result.returncode}): {result.stderr.strip()}"
            )
        duration_str = result.stdout.strip()
        if not duration_str:
            raise RuntimeError("ffprobe returned empty duration")
        return float(duration_str)
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg/ffprobe not found. Please install FFmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html\n"
            "  Linux: sudo apt install ffmpeg"
        )
    except ValueError:
        raise RuntimeError(f"Could not parse duration from ffprobe output: {duration_str}")


def get_frame_count(duration_seconds: float) -> int:
    """
    Calculate number of frames to extract based on video duration.
    
    Rules from spec Section 3.2:
    - Under 30 seconds: 3 frames (10%, 50%, 90%)
    - 30 sec — 2 minutes: 5 frames (10%, 30%, 50%, 70%, 90%)
    - 2 — 5 minutes: 7 frames (even distribution)
    - 5 — 15 minutes: 10 frames (every ~90 seconds)
    - 15 — 30 minutes: 12 frames (even distribution)
    - Over 30 minutes: 15 frames (every ~2 minutes)
    
    Hard limit: Never exceed 20 frames (Claude API limit).
    """
    if duration_seconds < 30:
        return 3
    elif duration_seconds < 120:  # < 2 minutes
        return 5
    elif duration_seconds < 300:  # < 5 minutes
        return 7
    elif duration_seconds < 900:  # < 15 minutes
        return 10
    elif duration_seconds < 1800:  # < 30 minutes
        return 12
    else:
        return 15  # 30+ minutes


def get_extraction_points(duration_seconds: float, num_frames: int) -> List[float]:
    """
    Calculate timestamp positions for frame extraction.
    
    For short videos (< 30s) with 3 frames: use 10%, 50%, 90%.
    For standard videos (30s-2min) with 5 frames: use 10%, 30%, 50%, 70%, 90%.
    For longer videos: distribute evenly.
    
    Returns list of timestamps in seconds.
    """
    if num_frames == 3:
        # Under 30 seconds: 10%, 50%, 90%
        percentages = [0.10, 0.50, 0.90]
    elif num_frames == 5:
        # 30 sec - 2 minutes: 10%, 30%, 50%, 70%, 90%
        percentages = [0.10, 0.30, 0.50, 0.70, 0.90]
    else:
        # Even distribution across the video
        percentages = [i / (num_frames - 1) for i in range(num_frames)]
    
    # Ensure first frame isn't at 0.0 and last frame isn't beyond duration
    timestamps = []
    for pct in percentages:
        ts = duration_seconds * pct
        # Clamp to valid range
        ts = max(0.1, min(ts, duration_seconds - 0.1))
        timestamps.append(ts)
    
    return timestamps


def extract_single_frame(
    video_path: str, timestamp: float, output_path: str, max_width: int = 1024
) -> Optional[str]:
    """
    Extract a single frame from a video at the given timestamp.
    Resizes to max_width while maintaining aspect ratio.
    
    Args:
        video_path: Path to the video file.
        timestamp: Time position in seconds.
        output_path: Where to save the extracted frame.
        max_width: Maximum width in pixels (default 1024).
    
    Returns:
        The output path if successful, None otherwise.
    """
    try:
        # Step 1: Extract frame at timestamp
        subprocess.run(
            [
                "ffmpeg", "-ss", str(timestamp), "-i", video_path,
                "-vframes", "1", "-q:v", str(settings.frame_quality),
                "-vf", f"scale={max_width}:-1",
                output_path, "-y",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        path = Path(output_path)
        if path.exists() and path.stat().st_size > 0:
            return output_path
        else:
            logger.warning(f"Frame extraction produced empty file: {output_path}")
            return None
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timed out extracting frame at {timestamp}s")
        return None
    except Exception as e:
        logger.error(f"Failed to extract frame at {timestamp}s: {e}")
        return None


def extract_frames(
    video_path: str, num_frames: int, output_dir: str, max_width: int = 1024
) -> List[str]:
    """
    Extract multiple frames from a video in parallel.
    
    Args:
        video_path: Path to the video file.
        num_frames: Number of frames to extract.
        output_dir: Directory to save extracted frames.
        max_width: Maximum width for resizing.
    
    Returns:
        List of paths to successfully extracted frames.
    """
    duration = get_video_duration(video_path)
    timestamps = get_extraction_points(duration, num_frames)
    
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    frame_paths = []
    tasks = []
    
    # Use ThreadPoolExecutor for parallel frame extraction
    with ThreadPoolExecutor(max_workers=min(num_frames, 8)) as executor:
        for i, ts in enumerate(timestamps):
            output = str(output_dir_path / f"frame_{i:02d}.jpg")
            frame_paths.append(output)
            tasks.append(
                executor.submit(extract_single_frame, video_path, ts, output, max_width)
            )
        
        successful = 0
        for future in as_completed(tasks):
            if future.result() is not None:
                successful += 1
        
        logger.info(
            f"Extracted {successful}/{num_frames} frames from {Path(video_path).name}"
        )
    
    # Return only successfully extracted frames
    return [p for p in frame_paths if Path(p).exists() and Path(p).stat().st_size > 0]


def get_video_properties(video_path: str) -> Dict[str, Any]:
    """
    Extract comprehensive video properties using ffprobe.
    
    Returns properties including:
    - date_created: Creation date from metadata (if available)
    - duration_seconds: Duration in seconds
    - frame_rate: Frame rate as string (e.g., "29.97 fps")
    - resolution: Width x Height (e.g., "1920x1080")
    - aspect_ratio: Display aspect ratio (e.g., "16:9")
    - bitrate_kbps: Overall bitrate in kbps
    - audio: Audio codec description (e.g., "AAC, 2 channels, 48kHz")
    
    Args:
        video_path: Path to the video file.
    
    Returns:
        Dictionary of video properties.
    
    Raises:
        RuntimeError: If ffprobe fails.
    """
    properties: Dict[str, Any] = {}
    
    try:
        # Run ffprobe with JSON output to get format + first video stream + first audio stream
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_format",
                "-show_streams",
                "-of", "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed (exit code {result.returncode}): {result.stderr.strip()}"
            )
        
        data = json.loads(result.stdout)
        
        # ── Format-level properties ────────────────────────────────────────
        fmt = data.get("format", {})
        tags = fmt.get("tags", {})
        
        # date_created — convert ISO date to DD/MM/YYYY
        date_created = (
            tags.get("creation_time") or
            tags.get("date") or
            tags.get("DATE") or
            ""
        )
        if date_created:
            # Parse ISO date: "2024-03-15T10:30:00.000000Z" → "15/03/2024"
            try:
                from datetime import datetime
                # Extract the date portion
                iso_date = date_created.replace("T", " ").split(".")[0].split("+")[0].split("Z")[0].strip()
                dt = datetime.fromisoformat(iso_date)
                date_created = dt.strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                # Fallback: keep as-is
                pass
        properties["date_created"] = date_created if date_created else None
        
        # duration
        duration_str = fmt.get("duration")
        properties["duration_seconds"] = round(float(duration_str), 2) if duration_str else None
        
        # bitrate
        bitrate_str = fmt.get("bit_rate")
        properties["bitrate_kbps"] = round(int(bitrate_str) / 1000) if bitrate_str else None
        
        # ── Stream-level properties ────────────────────────────────────────
        streams = data.get("streams", [])
        video_stream = None
        audio_stream = None
        
        for s in streams:
            if s.get("codec_type") == "video" and video_stream is None:
                video_stream = s
            elif s.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = s
        
        # Video stream
        if video_stream:
            # resolution
            width = video_stream.get("width")
            height = video_stream.get("height")
            if width and height:
                properties["resolution"] = f"{width}x{height}"
            else:
                properties["resolution"] = None
            
            # aspect_ratio — simplify to lowest terms and pad with zeros (e.g., "16:09")
            dar = video_stream.get("display_aspect_ratio")
            if not dar or dar == "0:1":
                if width and height:
                    dar = f"{width}:{height}"
            if dar and ":" in dar:
                parts = dar.split(":")
                if len(parts) == 2:
                    try:
                        w = int(parts[0])
                        h = int(parts[1])
                        # Reduce to lowest terms via GCD
                        gcd_val = _gcd(w, h)
                        w //= gcd_val
                        h //= gcd_val
                        dar = f"{w:02d}:{h:02d}"
                    except ValueError:
                        pass
            properties["aspect_ratio"] = dar or None
            
            # frame_rate
            r_frame_rate = video_stream.get("r_frame_rate", "")
            avg_frame_rate = video_stream.get("avg_frame_rate", "")
            # Prefer r_frame_rate, fall back to avg_frame_rate
            frame_rate_str = r_frame_rate or avg_frame_rate
            if frame_rate_str and "/" in frame_rate_str:
                try:
                    num, den = frame_rate_str.split("/")
                    num, den = float(num), float(den)
                    if den > 0:
                        fps = round(num / den, 3)
                        # Show with clean formatting
                        if fps == round(fps):
                            properties["frame_rate"] = f"{int(fps)} fps"
                        else:
                            properties["frame_rate"] = f"{fps:.2f} fps"
                    else:
                        properties["frame_rate"] = None
                except (ValueError, ZeroDivisionError):
                    properties["frame_rate"] = frame_rate_str
            else:
                properties["frame_rate"] = frame_rate_str or None
        else:
            properties["resolution"] = None
            properties["aspect_ratio"] = None
            properties["frame_rate"] = None
        
        # Audio stream
        if audio_stream:
            codec_name = audio_stream.get("codec_name", "").upper()
            channels = audio_stream.get("channels")
            sample_rate = audio_stream.get("sample_rate", "")
            
            parts = [codec_name] if codec_name else []
            if channels:
                parts.append(f"{channels} channel{'s' if channels > 1 else ''}")
            if sample_rate:
                try:
                    sr_khz = round(int(sample_rate) / 1000, 1)
                    parts.append(f"{sr_khz}kHz")
                except ValueError:
                    parts.append(f"{sample_rate}Hz")
            properties["audio"] = ", ".join(parts) if parts else None
        else:
            properties["audio"] = "No"
        
        logger.info(
            f"Video properties for {Path(video_path).name}: "
            f"{properties.get('resolution', 'N/A')}, "
            f"{properties.get('frame_rate', 'N/A')}, "
            f"{properties.get('duration_seconds', 'N/A')}s"
        )
        return properties
        
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg/ffprobe not found. Please install FFmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html\n"
            "  Linux: sudo apt install ffmpeg"
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ffprobe JSON output: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to get video properties: {e}")


def _gcd(a: int, b: int) -> int:
    """Compute greatest common divisor of two integers."""
    while b:
        a, b = b, a % b
    return a


def is_video_file(file_path: str) -> bool:
    """Check if a file is a supported video format by verifying with ffprobe."""
    ext = Path(file_path).suffix.lower()
    if ext not in settings.allowed_video_extensions:
        return False
    try:
        get_video_duration(file_path)
        return True
    except Exception:
        return False


def detect_scene_changes(
    video_path: str,
    sensitivity: float = 0.3,
    max_scenes: int = 20,
) -> List[float]:
    """
    Detect scene changes in a video using FFmpeg's scene detection filter.
    
    Uses the select=gt(scene\,sensitivity) filter to identify scene boundaries.
    Returns timestamps (in seconds) of detected scene changes.
    
    Args:
        video_path: Path to the video file.
        sensitivity: Scene change threshold (0.1=very sensitive, 0.5=less sensitive).
                     Default 0.3 works well for most content.
        max_scenes: Maximum number of scene timestamps to return (hard limit).
    
    Returns:
        List of timestamps in seconds where scene changes were detected.
    
    Raises:
        RuntimeError: If ffmpeg fails.
    """
    try:
        logger.info(
            f"Detecting scene changes in {Path(video_path).name} "
            f"(sensitivity={sensitivity}, max_scenes={max_scenes})"
        )
        
        result = subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-filter:v", f"select=gt(scene\\,{sensitivity}),showinfo",
                "-vsync", "vfr",
                "-f", "null", "-",
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for long videos
        )
        
        # Parse showinfo output to extract timestamps
        # Format: "pts_time:123.456" in stderr
        timestamps = []
        for line in result.stderr.split("\n"):
            if "pts_time:" in line:
                try:
                    # Extract the pts_time value
                    pts_part = line.split("pts_time:")[1].split()[0].strip()
                    ts = float(pts_part)
                    timestamps.append(ts)
                except (ValueError, IndexError):
                    continue
        
        # Deduplicate and sort
        timestamps = sorted(set(timestamps))
        
        # Limit to max_scenes
        if len(timestamps) > max_scenes:
            # Sample evenly from detected scenes
            step = len(timestamps) / max_scenes
            timestamps = [timestamps[int(i * step)] for i in range(max_scenes)]
        
        logger.info(
            f"Detected {len(timestamps)} scene changes in {Path(video_path).name}"
        )
        return timestamps
        
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg/ffprobe not found. Please install FFmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html\n"
            "  Linux: sudo apt install ffmpeg"
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Scene detection timed out for {video_path}")
        return []
    except Exception as e:
        logger.warning(f"Scene detection failed for {video_path}: {e}")
        return []


def extract_frames_at_scenes(
    video_path: str,
    output_dir: str,
    max_width: int = 1024,
    sensitivity: float = 0.3,
    max_frames: int = 15,
) -> List[str]:
    """
    Extract frames at detected scene changes using scene-aware extraction.
    
    This is the Phase 2 advanced extraction method. It detects meaningful
    scene transitions and extracts frames at those points instead of using
    fixed time intervals.
    
    Falls back to percentage-based extraction if scene detection fails
    or returns too few frames.
    
    Args:
        video_path: Path to the video file.
        output_dir: Directory to save extracted frames.
        max_width: Maximum width for resizing.
        sensitivity: Scene change sensitivity (0.1-0.5).
        max_frames: Maximum number of frames to extract.
    
    Returns:
        List of paths to successfully extracted frames.
    """
    duration = get_video_duration(video_path)
    
    # Try scene detection first
    scene_timestamps = detect_scene_changes(video_path, sensitivity, max_frames)
    
    # If scene detection returns enough frames, use those
    if len(scene_timestamps) >= 3:
        timestamps = scene_timestamps
        logger.info(
            f"Using scene-aware extraction: {len(timestamps)} frames "
            f"from {Path(video_path).name}"
        )
    else:
        # Fall back to percentage-based extraction
        num_frames = get_frame_count(duration)
        timestamps = get_extraction_points(duration, num_frames)
        logger.info(
            f"Scene detection returned {len(scene_timestamps)} frames, "
            f"falling back to {len(timestamps)} percentage-based frames"
        )
    
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    frame_paths = []
    tasks = []
    
    with ThreadPoolExecutor(max_workers=min(len(timestamps), 8)) as executor:
        for i, ts in enumerate(timestamps[:max_frames]):
            output = str(output_dir_path / f"frame_{i:02d}.jpg")
            frame_paths.append(output)
            tasks.append(
                executor.submit(extract_single_frame, video_path, ts, output, max_width)
            )
        
        successful = 0
        for future in as_completed(tasks):
            if future.result() is not None:
                successful += 1
        
        logger.info(
            f"Extracted {successful}/{len(timestamps)} frames from "
            f"{Path(video_path).name}"
        )
    
    return [p for p in frame_paths if Path(p).exists() and Path(p).stat().st_size > 0]
