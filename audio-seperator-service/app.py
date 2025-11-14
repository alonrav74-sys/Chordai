from flask import Flask, request, jsonify
import subprocess
import os
import tempfile
import shutil

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

@app.route('/separate', methods=['POST'])
def separate():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file"}), 400
        
        audio_file = request.files['audio']
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, 'input.mp3')
        audio_file.save(input_path)
        
        # Run Demucs
        subprocess.run(['demucs', '-n', 'htdemucs', input_path, '-o', temp_dir], check=True)
        
        # Output is in temp_dir/htdemucs/input/
        output_dir = os.path.join(temp_dir, 'htdemucs', 'input')
        
        vocals_path = os.path.join(output_dir, 'vocals.wav')
        music_path = os.path.join(output_dir, 'no_vocals.wav')
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return jsonify({
            "success": True,
            "message": "Separated successfully"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)