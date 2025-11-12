import librosa
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ChordDetector:
    """Detects chords from audio using harmonic analysis"""
    
    # Chord templates (major, minor, 7th, etc.)
    CHORD_TEMPLATES = {
        'C': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],   # C major: C E G
        'C#': [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],  # C# major
        'D': [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],   # D major
        'D#': [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],  # D# major
        'E': [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],   # E major
        'F': [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],   # F major
        'F#': [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],  # F# major
        'G': [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],   # G major
        'G#': [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],  # G# major
        'A': [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],   # A major
        'A#': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],  # A# major
        'B': [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1],   # B major
        
        # Minor chords
        'Cm': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],  # C minor: C Eb G
        'C#m': [0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0], # C# minor
        'Dm': [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],  # D minor
        'D#m': [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0], # D# minor
        'Em': [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],  # E minor
        'Fm': [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],  # F minor
        'F#m': [0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0], # F# minor
        'Gm': [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0],  # G minor
        'G#m': [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1], # G# minor
        'Am': [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],  # A minor
        'A#m': [0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0], # A# minor
        'Bm': [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],  # B minor
    }
    
    def __init__(self, hop_length=512, min_confidence=0.3):
        """
        Initialize chord detector
        
        Args:
            hop_length: Number of samples between frames
            min_confidence: Minimum confidence threshold for chord detection
        """
        self.hop_length = hop_length
        self.min_confidence = min_confidence
    
    def detect_chords(self, audio_path: str, 
                     frame_duration: float = 0.5) -> Dict[str, Any]:
        """
        Detect chords from audio file
        
        Args:
            audio_path: Path to audio file
            frame_duration: Duration of each analysis frame in seconds
        
        Returns:
            dict with detected chords and metadata
        """
        try:
            logger.info(f"Loading audio for chord detection: {audio_path}")
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050)
            duration = librosa.get_duration(y=y, sr=sr)
            
            logger.info(f"Audio loaded: {duration:.2f} seconds at {sr} Hz")
            
            # Calculate chromagram (pitch class profiles)
            hop_length = int(sr * frame_duration)
            chroma = librosa.feature.chroma_cqt(
                y=y, 
                sr=sr, 
                hop_length=hop_length
            )
            
            logger.info(f"Chromagram shape: {chroma.shape}")
            
            # Detect chords frame by frame
            chords = []
            times = librosa.frames_to_time(
                np.arange(chroma.shape[1]), 
                sr=sr, 
                hop_length=hop_length
            )
            
            prev_chord = None
            chord_start_time = 0
            
            for i, time in enumerate(times):
                # Get chroma vector for this frame
                chroma_frame = chroma[:, i]
                
                # Normalize
                chroma_frame = chroma_frame / (np.sum(chroma_frame) + 1e-8)
                
                # Find best matching chord
                chord, confidence = self._match_chord(chroma_frame)
                
                # Only add chord if confidence is above threshold
                if confidence >= self.min_confidence:
                    # Merge consecutive identical chords
                    if chord != prev_chord:
                        if prev_chord is not None:
                            chords.append({
                                "time": chord_start_time,
                                "chord": prev_chord,
                                "confidence": round(confidence, 3),
                                "duration": round(time - chord_start_time, 3)
                            })
                        chord_start_time = time
                        prev_chord = chord
            
            # Add final chord
            if prev_chord is not None:
                chords.append({
                    "time": chord_start_time,
                    "chord": prev_chord,
                    "confidence": round(confidence, 3),
                    "duration": round(duration - chord_start_time, 3)
                })
            
            logger.info(f"Detected {len(chords)} chord changes")
            
            return {
                "success": True,
                "chords": chords,
                "duration": duration,
                "sample_rate": sr
            }
        
        except Exception as e:
            logger.error(f"Error detecting chords: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chords": []
            }
    
    def _match_chord(self, chroma_vector):
        """
        Match chroma vector to chord template
        
        Args:
            chroma_vector: 12-dimensional chroma vector
        
        Returns:
            tuple of (chord_name, confidence)
        """
        best_chord = "N"  # No chord
        best_score = 0
        
        for chord_name, template in self.CHORD_TEMPLATES.items():
            # Calculate correlation between chroma and template
            template_array = np.array(template, dtype=float)
            template_array = template_array / (np.sum(template_array) + 1e-8)
            
            # Cosine similarity
            score = np.dot(chroma_vector, template_array) / (
                np.linalg.norm(chroma_vector) * np.linalg.norm(template_array) + 1e-8
            )
            
            if score > best_score:
                best_score = score
                best_chord = chord_name
        
        return best_chord, best_score
