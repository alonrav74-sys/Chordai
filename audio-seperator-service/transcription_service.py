import os
import logging
import requests
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Handles transcription using various Whisper APIs"""
    
    def __init__(self):
        self.assemblyai_base_url = "https://api.assemblyai.com/v2"
        self.groq_base_url = "https://api.groq.com/openai/v1"
    
    def transcribe(self, audio_path: str, api_key: Optional[str] = None, 
                   service: str = 'assemblyai') -> Dict[str, Any]:
        """
        Transcribe audio file using specified service
        
        Args:
            audio_path: Path to audio file
            api_key: API key for the service
            service: 'assemblyai' or 'groq'
        
        Returns:
            dict with transcription results
        """
        if not api_key:
            # Try to get from environment
            if service == 'assemblyai':
                api_key = os.environ.get('ASSEMBLYAI_API_KEY')
            elif service == 'groq':
                api_key = os.environ.get('GROQ_API_KEY')
        
        if not api_key:
            logger.warning(f"No API key provided for {service}")
            return {
                "success": False,
                "error": f"No API key provided for {service}"
            }
        
        try:
            if service == 'assemblyai':
                return self._transcribe_assemblyai(audio_path, api_key)
            elif service == 'groq':
                return self._transcribe_groq(audio_path, api_key)
            else:
                return {
                    "success": False,
                    "error": f"Unknown service: {service}"
                }
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _transcribe_assemblyai(self, audio_path: str, api_key: str) -> Dict[str, Any]:
        """Transcribe using AssemblyAI with word-level timestamps"""
        headers = {"authorization": api_key}
        
        # Step 1: Upload audio file
        logger.info("Uploading audio to AssemblyAI...")
        with open(audio_path, 'rb') as f:
            upload_response = requests.post(
                f"{self.assemblyai_base_url}/upload",
                headers=headers,
                data=f
            )
        
        if upload_response.status_code != 200:
            return {
                "success": False,
                "error": f"Upload failed: {upload_response.text}"
            }
        
        audio_url = upload_response.json()['upload_url']
        logger.info(f"Audio uploaded: {audio_url}")
        
        # Step 2: Request transcription with word-level timestamps
        logger.info("Requesting transcription...")
        transcript_response = requests.post(
            f"{self.assemblyai_base_url}/transcript",
            headers=headers,
            json={
                "audio_url": audio_url,
                "word_boost": [],
                "boost_param": "default"
            }
        )
        
        if transcript_response.status_code != 200:
            return {
                "success": False,
                "error": f"Transcription request failed: {transcript_response.text}"
            }
        
        transcript_id = transcript_response.json()['id']
        logger.info(f"Transcription job created: {transcript_id}")
        
        # Step 3: Poll for completion
        while True:
            status_response = requests.get(
                f"{self.assemblyai_base_url}/transcript/{transcript_id}",
                headers=headers
            )
            
            status_data = status_response.json()
            status = status_data['status']
            
            logger.info(f"Transcription status: {status}")
            
            if status == 'completed':
                # Extract word-level timestamps
                words = []
                if 'words' in status_data:
                    for word in status_data['words']:
                        words.append({
                            "text": word['text'],
                            "start": word['start'] / 1000.0,  # Convert ms to seconds
                            "end": word['end'] / 1000.0,
                            "confidence": word['confidence']
                        })
                
                return {
                    "success": True,
                    "text": status_data['text'],
                    "words": words,
                    "confidence": status_data.get('confidence', 0),
                    "service": "assemblyai"
                }
            
            elif status == 'error':
                return {
                    "success": False,
                    "error": status_data.get('error', 'Transcription failed')
                }
            
            # Wait before polling again
            time.sleep(3)
    
    def _transcribe_groq(self, audio_path: str, api_key: str) -> Dict[str, Any]:
        """Transcribe using Groq Whisper API with timestamps"""
        logger.info("Transcribing with Groq Whisper...")
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        with open(audio_path, 'rb') as audio_file:
            files = {
                'file': (os.path.basename(audio_path), audio_file, 'audio/wav'),
            }
            data = {
                'model': 'whisper-large-v3',
                'response_format': 'verbose_json',  # Get word-level timestamps
                'timestamp_granularities': 'word'
            }
            
            response = requests.post(
                f"{self.groq_base_url}/audio/transcriptions",
                headers=headers,
                files=files,
                data=data
            )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Groq API error: {response.text}"
            }
        
        result = response.json()
        
        # Extract word-level timestamps if available
        words = []
        if 'words' in result:
            for word in result['words']:
                words.append({
                    "text": word['word'],
                    "start": word['start'],
                    "end": word['end'],
                    "confidence": 1.0  # Groq doesn't provide confidence
                })
        
        # If no words but segments available, extract from segments
        elif 'segments' in result:
            for segment in result['segments']:
                # Split segment text into approximate words
                segment_words = segment['text'].strip().split()
                segment_duration = segment['end'] - segment['start']
                word_duration = segment_duration / len(segment_words) if segment_words else 0
                
                for i, word_text in enumerate(segment_words):
                    word_start = segment['start'] + (i * word_duration)
                    words.append({
                        "text": word_text,
                        "start": word_start,
                        "end": word_start + word_duration,
                        "confidence": 1.0
                    })
        
        return {
            "success": True,
            "text": result.get('text', ''),
            "words": words,
            "segments": result.get('segments', []),
            "service": "groq"
        }
