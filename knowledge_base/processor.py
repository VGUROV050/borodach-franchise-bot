# Video processor for Knowledge Base
# Extracts audio, transcribes with Whisper, creates embeddings

import os
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

from openai import AsyncOpenAI

from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Paths
VIDEOS_DIR = Path(__file__).parent / "videos"
TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"
AUDIO_DIR = Path(__file__).parent / "audio"

# Ensure directories exist
VIDEOS_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)


class VideoProcessor:
    """Processes videos: extracts audio, transcribes, creates embeddings."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
    def extract_audio(self, video_path: Path) -> Optional[Path]:
        """
        Extract audio from video using ffmpeg.
        Returns path to audio file or None on error.
        """
        audio_path = AUDIO_DIR / f"{video_path.stem}.mp3"
        
        if audio_path.exists():
            logger.info(f"Audio already exists: {audio_path}")
            return audio_path
        
        try:
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "libmp3lame",
                "-ab", "64k",  # Lower bitrate for smaller files
                "-ar", "16000",  # 16kHz sample rate (optimal for Whisper)
                "-ac", "1",  # Mono
                "-y",  # Overwrite
                str(audio_path)
            ]
            
            logger.info(f"Extracting audio: {video_path.name}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg error: {result.stderr}")
                return None
                
            logger.info(f"Audio extracted: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return None
    
    def split_audio(self, audio_path: Path, segment_duration: int = 600) -> list[Path]:
        """
        Split large audio file into smaller segments.
        Whisper API has 25MB limit, so we split into ~10 min chunks.
        
        Args:
            audio_path: Path to audio file
            segment_duration: Duration of each segment in seconds (default 10 min)
        
        Returns:
            List of paths to audio segments
        """
        # Check file size (25MB limit for Whisper)
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb <= 24:  # Under limit, no need to split
            logger.info(f"Audio file {file_size_mb:.1f}MB - no split needed")
            return [audio_path]
        
        logger.info(f"Audio file {file_size_mb:.1f}MB - splitting into {segment_duration}s segments")
        
        # Get audio duration
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                capture_output=True, text=True
            )
            total_duration = float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return [audio_path]
        
        # Calculate number of segments
        num_segments = int(total_duration / segment_duration) + 1
        logger.info(f"Splitting {total_duration:.0f}s audio into {num_segments} segments")
        
        segments = []
        for i in range(num_segments):
            start_time = i * segment_duration
            segment_path = AUDIO_DIR / f"{audio_path.stem}_part{i:03d}.mp3"
            
            if segment_path.exists():
                segments.append(segment_path)
                continue
            
            try:
                cmd = [
                    "ffmpeg", "-i", str(audio_path),
                    "-ss", str(start_time),
                    "-t", str(segment_duration),
                    "-acodec", "libmp3lame",
                    "-ab", "64k",
                    "-ar", "16000",
                    "-ac", "1",
                    "-y",
                    str(segment_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and segment_path.exists():
                    segments.append(segment_path)
                    logger.info(f"Created segment {i+1}/{num_segments}: {segment_path.name}")
                else:
                    logger.error(f"Failed to create segment {i}: {result.stderr}")
                    
            except Exception as e:
                logger.error(f"Error creating segment {i}: {e}")
        
        return segments

    async def transcribe_audio(self, audio_path: Path) -> Optional[dict]:
        """
        Transcribe audio using OpenAI Whisper API.
        Automatically splits large files into segments.
        Returns transcript with timestamps.
        """
        transcript_path = TRANSCRIPTS_DIR / f"{audio_path.stem}.json"
        
        # Check if already transcribed
        if transcript_path.exists():
            logger.info(f"Transcript already exists: {transcript_path}")
            with open(transcript_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        if not self.client:
            logger.error("OpenAI client not configured")
            return None
        
        try:
            # Split audio if needed
            audio_segments = self.split_audio(audio_path)
            
            all_segments = []
            total_duration = 0
            full_text = ""
            time_offset = 0
            segment_id = 0
            
            for seg_idx, segment_path in enumerate(audio_segments):
                logger.info(f"Transcribing segment {seg_idx + 1}/{len(audio_segments)}: {segment_path.name}")
                
                with open(segment_path, "rb") as audio_file:
                    response = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ru",
                        response_format="verbose_json",
                        timestamp_granularities=["segment"]
                    )
                
                # Get segment duration for offset calculation
                seg_duration = getattr(response, 'duration', 0)
                
                # Process segments with time offset
                for seg in response.segments:
                    if hasattr(seg, 'id'):
                        all_segments.append({
                            "id": segment_id,
                            "start": seg.start + time_offset,
                            "end": seg.end + time_offset,
                            "text": seg.text.strip() if hasattr(seg.text, 'strip') else str(seg.text).strip()
                        })
                    else:
                        all_segments.append({
                            "id": segment_id,
                            "start": seg.get('start', 0) + time_offset,
                            "end": seg.get('end', 0) + time_offset,
                            "text": str(seg.get('text', '')).strip()
                        })
                    segment_id += 1
                
                # Append text
                seg_text = getattr(response, 'text', '')
                if full_text:
                    full_text += " " + seg_text
                else:
                    full_text = seg_text
                
                time_offset += seg_duration
                total_duration += seg_duration
                
                logger.info(f"Segment {seg_idx + 1} transcribed: {seg_duration:.1f}s")
                
                # Small delay between API calls
                if seg_idx < len(audio_segments) - 1:
                    await asyncio.sleep(1)
            
            # Clean up segment files if we split the audio
            if len(audio_segments) > 1:
                for seg_path in audio_segments:
                    if seg_path != audio_path and seg_path.exists():
                        try:
                            seg_path.unlink()
                            logger.info(f"Cleaned up: {seg_path.name}")
                        except Exception:
                            pass
            
            transcript = {
                "filename": audio_path.stem,
                "language": "ru",
                "duration": total_duration,
                "text": full_text,
                "segments": all_segments
            }
            
            # Save transcript
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Transcribed: {audio_path.name} ({total_duration:.1f}s total, {len(all_segments)} segments)")
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing: {e}")
            return None
    
    def chunk_transcript(
        self, 
        transcript: dict, 
        max_words: int = 300,
        overlap_words: int = 50
    ) -> list[dict]:
        """
        Split transcript into overlapping chunks for RAG.
        Each chunk contains ~300 words with timestamps.
        """
        segments = transcript.get("segments", [])
        if not segments:
            return []
        
        chunks = []
        current_chunk = {
            "text": "",
            "start_time": segments[0]["start"],
            "end_time": 0,
            "word_count": 0
        }
        
        for seg in segments:
            seg_text = seg["text"].strip()
            seg_words = len(seg_text.split())
            
            # Add segment to current chunk
            if current_chunk["text"]:
                current_chunk["text"] += " " + seg_text
            else:
                current_chunk["text"] = seg_text
            current_chunk["end_time"] = seg["end"]
            current_chunk["word_count"] += seg_words
            
            # Check if chunk is big enough
            if current_chunk["word_count"] >= max_words:
                chunks.append(current_chunk.copy())
                
                # Start new chunk with overlap
                # Find overlap point
                words = current_chunk["text"].split()
                overlap_text = " ".join(words[-overlap_words:]) if len(words) > overlap_words else current_chunk["text"]
                
                current_chunk = {
                    "text": overlap_text,
                    "start_time": seg["start"],  # Approximate
                    "end_time": 0,
                    "word_count": len(overlap_text.split())
                }
        
        # Add last chunk if not empty
        if current_chunk["text"] and current_chunk["word_count"] >= 50:
            chunks.append(current_chunk)
        
        # Add chunk indices
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i
        
        logger.info(f"Created {len(chunks)} chunks from transcript")
        return chunks
    
    async def create_embedding(self, text: str) -> Optional[list[float]]:
        """Create embedding for text using OpenAI."""
        if not self.client:
            logger.error("OpenAI client not configured")
            return None
        
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None
    
    async def process_video(self, video_path: Path) -> Optional[dict]:
        """
        Full pipeline: extract audio -> transcribe -> chunk.
        Returns processed data or None on error.
        """
        logger.info(f"Processing video: {video_path.name}")
        
        # Step 1: Extract audio
        audio_path = self.extract_audio(video_path)
        if not audio_path:
            return None
        
        # Step 2: Transcribe
        transcript = await self.transcribe_audio(audio_path)
        if not transcript:
            return None
        
        # Step 3: Chunk
        chunks = self.chunk_transcript(transcript)
        
        return {
            "video_filename": video_path.name,
            "audio_filename": audio_path.name,
            "duration": transcript.get("duration", 0),
            "full_text": transcript.get("text", ""),
            "chunks": chunks
        }
    
    async def process_module(self, module_path: Path) -> list[dict]:
        """Process all videos in a module directory."""
        results = []
        
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        videos = sorted([
            f for f in module_path.iterdir() 
            if f.suffix.lower() in video_extensions
        ])
        
        logger.info(f"Found {len(videos)} videos in {module_path.name}")
        
        for video in videos:
            result = await self.process_video(video)
            if result:
                results.append(result)
        
        return results


# CLI for testing
async def main():
    """Test processing a single video."""
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python processor.py <video_path>")
        print("Example: python processor.py knowledge_base/videos/module1/lesson1.mp4")
        return
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"File not found: {video_path}")
        return
    
    processor = VideoProcessor()
    result = await processor.process_video(video_path)
    
    if result:
        print(f"\n✅ Processed: {result['video_filename']}")
        print(f"Duration: {result['duration']:.1f}s")
        print(f"Chunks: {len(result['chunks'])}")
        print(f"\nFirst chunk preview:")
        if result['chunks']:
            chunk = result['chunks'][0]
            print(f"  [{chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s]")
            print(f"  {chunk['text'][:200]}...")
    else:
        print("❌ Processing failed")


if __name__ == "__main__":
    asyncio.run(main())

