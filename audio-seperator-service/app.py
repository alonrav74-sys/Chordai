from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import logging
from audio_processor import AudioProcessor
from transcription_service import TranscriptionService
from chord_detector import ChordDetector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize services
audio_processor = AudioProcessor()
transcription_service = TranscriptionService()
chord_detector = ChordDetector()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Audio Separator Service",
        "version": "1.0.0"
    })

@app.route('/process-audio', methods=['POST'])
def process_audio():
    """
    Main endpoint - receives audio file, separates, transcribes vocals and detects chords
    
    Expected input:
    - audio file (multipart/form-data)
    - whisper_api_key (optional, form field)
    - whisper_service (optional: 'assemblyai' or 'groq', default: 'assemblyai')
    
    Returns:
    {
        "success": true,
        "transcription": {
            "text": "...",
            "words": [...],
            "segments": [...]
        },
        "chords": [
            {"time": 0.5, "chord": "C", "confidence": 0.95},
            ...
        ],
        "metadata": {
            "duration": 180.5,
            "sample_rate": 44100
        }
    }
    """
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({
                "success": False,
                "error": "No audio file provided"
            }), 400
        
        audio_file = request.files['audio']
        whisper_api_key = request.form.get('whisper_api_key')
        whisper_service = request.form.get('whisper_service', 'assemblyai')
        
        if not audio_file.filename:
            return jsonify({
                "success": False,
                "error": "Empty filename"
            }), 400
        
        logger.info(f"Processing audio file: {audio_file.filename}")
        
        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            input_path = os.path.join(temp_dir, "input_audio.mp3")
            audio_file.save(input_path)
            logger.info(f"Saved input file to {input_path}")
            
            # Step 1: Separate vocals and accompaniment using Spleeter
            logger.info("Separating vocals and accompaniment...")
            separation_result = audio_processor.separate_audio(input_path, temp_dir)
            
            if not separation_result['success']:
                return jsonify({
                    "success": False,
                    "error": separation_result['error']
                }), 500
            
            vocals_path = separation_result['vocals_path']
            accompaniment_path = separation_result['accompaniment_path']
            
            # Step 2: Transcribe vocals (parallel can be done, but sequential for now)
            logger.info("Transcribing vocals...")
            transcription_result = transcription_service.transcribe(
                vocals_path,
                api_key=whisper_api_key,
                service=whisper_service
            )
            
            # Step 3: Detect chords from accompaniment
            logger.info("Detecting chords...")
            chord_result = chord_detector.detect_chords(accompaniment_path)
            
            # Prepare response
            response = {
                "success": True,
                "transcription": transcription_result if transcription_result['success'] else None,
                "chords": chord_result['chords'] if chord_result['success'] else [],
                "metadata": {
                    "duration": separation_result.get('duration', 0),
                    "sample_rate": separation_result.get('sample_rate', 44100),
                    "transcription_service": whisper_service,
                    "transcription_success": transcription_result['success'],
                    "chord_detection_success": chord_result['success']
                }
            }
            
            if not transcription_result['success']:
                response['transcription_error'] = transcription_result.get('error', 'Unknown error')
            
            if not chord_result['success']:
                response['chord_error'] = chord_result.get('error', 'Unknown error')
            
            logger.info("Processing complete!")
            return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/separate-only', methods=['POST'])
def separate_only():
    """
    Endpoint to only separate audio without transcription/chord detection
    Returns paths to separated files (for testing)
    """
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file"}), 400
        
        audio_file = request.files['audio']
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp3")
            audio_file.save(input_path)
            
            result = audio_processor.separate_audio(input_path, temp_dir)
            
            return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in separation: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
