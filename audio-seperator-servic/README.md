# Audio Separator Microservice

Python microservice for separating audio into vocals and accompaniment, then processing each stream separately:
- **Vocals** → Whisper AI transcription (AssemblyAI or Groq)
- **Accompaniment** → Chord detection using harmonic analysis

## Architecture

```
Audio File (MP3/WAV)
    ↓
Spleeter Separation
    ├─→ Vocals → Whisper API → Transcription with word timestamps
    └─→ Accompaniment → Librosa → Chord detection
    ↓
Unified JSON Response
```

## Features

- 🎵 **Audio Separation**: Spleeter 2-stem separation (vocals/accompaniment)
- 🎤 **Transcription**: Support for AssemblyAI and Groq Whisper APIs
- 🎸 **Chord Detection**: Harmonic analysis with confidence scores
- ⏱️ **Word-level Timestamps**: Precise timing for lyrics synchronization
- 🐳 **Docker Ready**: Easy deployment with Docker Compose
- 🔌 **REST API**: Simple HTTP interface for any client

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (recommended)
- FFmpeg (for audio processing)

## Installation

### Option 1: Docker (Recommended)

1. Clone the repository:
```bash
git clone <your-repo>
cd audio-separator-service
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. Build and run:
```bash
docker-compose up --build
```

The service will be available at `http://localhost:5000`

### Option 2: Local Development

1. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1

# macOS
brew install ffmpeg libsndfile
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export ASSEMBLYAI_API_KEY=your_key_here
export GROQ_API_KEY=your_key_here
```

4. Run the service:
```bash
python app.py
```

## API Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Audio Separator Service",
  "version": "1.0.0"
}
```

### Process Audio
```http
POST /process-audio
```

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `audio`: Audio file (MP3, WAV, etc.)
  - `whisper_api_key` (optional): API key for transcription
  - `whisper_service` (optional): `"assemblyai"` or `"groq"` (default: `"assemblyai"`)

**Response:**
```json
{
  "success": true,
  "transcription": {
    "text": "Full transcription text...",
    "words": [
      {
        "text": "Hello",
        "start": 0.5,
        "end": 0.8,
        "confidence": 0.98
      }
    ],
    "service": "assemblyai"
  },
  "chords": [
    {
      "time": 0.5,
      "chord": "C",
      "confidence": 0.85,
      "duration": 2.0
    },
    {
      "time": 2.5,
      "chord": "Am",
      "confidence": 0.92,
      "duration": 1.5
    }
  ],
  "metadata": {
    "duration": 180.5,
    "sample_rate": 44100,
    "transcription_success": true,
    "chord_detection_success": true
  }
}
```

### Separate Only
```http
POST /separate-only
```

For testing separation without transcription/chord detection.

## Java Client Integration

### Add to your Spring Boot application

1. Copy `AudioSeparatorClient.java` to your project:
```
src/main/java/com/chordfinder/service/AudioSeparatorClient.java
```

2. Configure the service URL in `application.properties`:
```properties
audio.separator.service.url=http://localhost:5000
```

3. Use in your code:
```java
@Autowired
private AudioSeparatorClient audioSeparatorClient;

public void processYouTubeAudio(File audioFile) {
    // Check service health
    if (!audioSeparatorClient.isHealthy()) {
        throw new RuntimeException("Audio service unavailable");
    }
    
    // Process audio
    ProcessingResult result = audioSeparatorClient.processAudio(
        audioFile,
        assemblyAiApiKey,
        "assemblyai"
    );
    
    // Use results
    String lyrics = result.getTranscriptionText();
    List<ChordDetection> chords = result.getChords();
    List<WordTimestamp> words = result.getWords();
    
    // Synchronize and display...
}
```

## Integration with ChordFinder Pro

### Workflow:

1. **Download Audio** (Java):
```java
// Download from YouTube using RapidAPI
File audioFile = downloadFromYouTube(youtubeUrl);
```

2. **Send to Microservice** (Java → Python):
```java
ProcessingResult result = audioSeparatorClient.processAudio(
    audioFile, 
    whisperApiKey, 
    "assemblyai"
);
```

3. **Receive Results** (Python → Java):
```java
// Lyrics with word-level timestamps
for (WordTimestamp word : result.getWords()) {
    System.out.println(word.getText() + " at " + word.getStart() + "s");
}

// Chords with timing
for (ChordDetection chord : result.getChords()) {
    System.out.println(chord.getChord() + " at " + chord.getTime() + "s");
}
```

4. **Display in UI** (Java):
```java
// Synchronize chords with lyrics
syncChordsAndLyrics(result.getWords(), result.getChords());
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ASSEMBLYAI_API_KEY` | AssemblyAI API key | Optional* |
| `GROQ_API_KEY` | Groq API key | Optional* |
| `PORT` | Service port | No (default: 5000) |

*At least one API key is required for transcription

### Docker Configuration

Edit `docker-compose.yml` to customize:
- Port mapping
- Memory limits
- Volume mounts

## Performance

- **Separation**: ~20-40 seconds for 3-minute song
- **Transcription**: 
  - AssemblyAI: ~30-60 seconds
  - Groq: ~10-20 seconds
- **Chord Detection**: ~5-10 seconds

**Total**: 1-2 minutes for complete processing of 3-minute song

## Troubleshooting

### "Service unhealthy"
```bash
# Check logs
docker-compose logs audio-separator

# Restart service
docker-compose restart
```

### "Out of memory"
Increase Docker memory limits in `docker-compose.yml`:
```yaml
services:
  audio-separator:
    deploy:
      resources:
        limits:
          memory: 4G
```

### "Transcription failed"
- Verify API key is correct
- Check API quota/limits
- Try alternative service (AssemblyAI ↔ Groq)

### "Poor chord detection"
- Ensure audio quality is good
- Try adjusting `min_confidence` in `ChordDetector`
- Some genres (heavy metal, electronic) are harder to detect

## Development

### Running Tests
```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/
```

### Code Structure
```
audio-separator-service/
├── app.py                    # Main Flask application
├── audio_processor.py        # Spleeter separation
├── transcription_service.py  # Whisper API clients
├── chord_detector.py         # Chord detection
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker Compose config
└── java-client/             # Java integration
    ├── AudioSeparatorClient.java
    └── AudioProcessingExample.java
```

## API Keys

### AssemblyAI
Get your key at: https://www.assemblyai.com/
- Free tier: 5 hours/month
- Word-level timestamps included

### Groq
Get your key at: https://console.groq.com/
- Free tier available
- Very fast processing

## Future Enhancements

- [ ] Support for more stems (drums, bass, etc.)
- [ ] Better chord detection algorithm
- [ ] Support for more transcription services
- [ ] Batch processing endpoint
- [ ] WebSocket for real-time progress
- [ ] Key detection
- [ ] BPM detection

## License

MIT

## Contributing

Pull requests welcome! Please ensure:
- Code follows PEP 8
- Tests pass
- Documentation updated

## Support

For issues, please open a GitHub issue with:
- Service logs
- Sample audio file (if possible)
- Expected vs actual behavior
