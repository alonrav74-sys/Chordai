import os
import logging
from spleeter.separator import Separator
from spleeter.audio.adapter import AudioAdapter
import numpy as np

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handles audio separation using Spleeter"""
    
    def __init__(self):
        """Initialize Spleeter with 2 stems (vocals/accompaniment)"""
        try:
            # Initialize Spleeter separator with 2 stems
            self.separator = Separator('spleeter:2stems')
            self.audio_loader = AudioAdapter.default()
            logger.info("Spleeter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Spleeter: {str(e)}")
            raise
    
    def separate_audio(self, input_path, output_dir):
        """
        Separate audio into vocals and accompaniment
        
        Args:
            input_path: Path to input audio file
            output_dir: Directory to save separated files
        
        Returns:
            dict with success status, paths to separated files, and metadata
        """
        try:
            logger.info(f"Loading audio from {input_path}")
            
            # Load audio waveform
            waveform, sample_rate = self.audio_loader.load(
                input_path,
                sample_rate=44100  # Spleeter works best with 44100 Hz
            )
            
            # Get duration
            duration = len(waveform) / sample_rate
            logger.info(f"Audio duration: {duration:.2f} seconds, sample rate: {sample_rate}")
            
            # Perform separation
            logger.info("Performing audio separation...")
            prediction = self.separator.separate(waveform)
            
            # Save separated tracks
            vocals_path = os.path.join(output_dir, "vocals.wav")
            accompaniment_path = os.path.join(output_dir, "accompaniment.wav")
            
            # Spleeter returns dict with 'vocals' and 'accompaniment' keys
            self._save_audio(prediction['vocals'], vocals_path, sample_rate)
            self._save_audio(prediction['accompaniment'], accompaniment_path, sample_rate)
            
            logger.info(f"Separation complete. Vocals: {vocals_path}, Accompaniment: {accompaniment_path}")
            
            return {
                "success": True,
                "vocals_path": vocals_path,
                "accompaniment_path": accompaniment_path,
                "duration": duration,
                "sample_rate": sample_rate
            }
        
        except Exception as e:
            logger.error(f"Error during audio separation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _save_audio(self, audio_data, output_path, sample_rate):
        """Save audio data to WAV file"""
        import soundfile as sf
        
        # Ensure audio_data is in the right format
        if len(audio_data.shape) == 1:
            # Mono
            audio_data = audio_data.reshape(-1, 1)
        
        # Save as WAV
        sf.write(output_path, audio_data, sample_rate)
        logger.info(f"Saved audio to {output_path}")
