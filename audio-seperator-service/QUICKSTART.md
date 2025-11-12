# Quick Start - Audio Separator Microservice

## 🚀 Get Running in 5 Minutes

### 1. Prerequisites
- Docker & Docker Compose installed
- API key from AssemblyAI or Groq

### 2. Setup
```bash
# Clone/download the audio-separator-service folder
cd audio-separator-service

# Copy environment template
cp .env.example .env

# Edit .env and add your API key:
# ASSEMBLYAI_API_KEY=your_key_here
# or
# GROQ_API_KEY=your_key_here
```

### 3. Start Service
```bash
./start.sh
```

That's it! Service is now running on http://localhost:5000

### 4. Test It
```bash
# Health check
curl http://localhost:5000/health

# Process audio (replace with your audio file)
python test_client.py process your_song.mp3 YOUR_API_KEY assemblyai
```

## 📝 Integration with ChordFinder Pro

### Java Side:
```java
// 1. Copy the Java client to your project
src/main/java/com/chordfinder/service/AudioSeparatorClient.java

// 2. Add to application.properties
audio.separator.service.url=http://localhost:5000

// 3. Use it in your code
@Autowired
private AudioSeparatorClient audioSeparatorClient;

public void processYouTube(String youtubeUrl) {
    // Download audio from YouTube (your existing code)
    File audioFile = rapidApi.downloadAudio(youtubeUrl);
    
    // Send to microservice
    ProcessingResult result = audioSeparatorClient.processAudio(
        audioFile,
        whisperApiKey,
        "assemblyai"
    );
    
    // Get results
    String lyrics = result.getTranscriptionText();
    List<ChordDetection> chords = result.getChords();
    List<WordTimestamp> words = result.getWords();
    
    // Display synchronized lyrics + chords!
}
```

## 📦 Project Structure
```
audio-separator-service/
├── app.py                          # Main Flask API
├── audio_processor.py              # Spleeter separation
├── transcription_service.py        # Whisper integration  
├── chord_detector.py               # Chord detection
├── requirements.txt                # Dependencies
├── Dockerfile                      # Container config
├── docker-compose.yml              # Deployment config
├── start.sh                        # Quick start script
├── test_client.py                  # Test utility
├── .env.example                    # Config template
├── README.md                       # Full documentation
├── INTEGRATION_GUIDE.md            # ChordFinder Pro guide
├── OVERVIEW.md                     # System overview
└── java-client/                    # Java integration
    ├── AudioSeparatorClient.java
    └── AudioProcessingExample.java
```

## 🎯 What It Does

**Input:** Audio file (MP3/WAV) from YouTube
**Process:** 
1. Separates vocals from music (Spleeter)
2. Transcribes vocals with word timestamps (Whisper)
3. Detects chords from music (Librosa)

**Output:** JSON with:
- Complete lyrics text
- Word-level timestamps (for sync)
- Chord progression with timing
- Confidence scores

## 🔑 API Keys

Get your API key from:
- **AssemblyAI**: https://www.assemblyai.com/ (5 hours free/month)
- **Groq**: https://console.groq.com/ (generous free tier)

## ⚙️ Configuration

Edit `.env`:
```bash
# Choose one (or both):
ASSEMBLYAI_API_KEY=your_assemblyai_key_here
GROQ_API_KEY=your_groq_key_here

# Optional:
PORT=5000
```

## 🐛 Common Issues

**Port already in use:**
```bash
# Change port in docker-compose.yml
ports:
  - "5001:5000"  # Change 5000 to 5001
```

**Service not responding:**
```bash
# Check logs
docker-compose logs audio-separator

# Restart
docker-compose restart
```

**Poor transcription quality:**
- Make sure API key is valid
- Try higher quality audio
- Try different service (assemblyai ↔ groq)

## 📖 Full Documentation

- **README.md** - Complete setup guide
- **INTEGRATION_GUIDE.md** - ChordFinder Pro integration steps
- **OVERVIEW.md** - Architecture and technical details

## 🛑 Stop Service
```bash
docker-compose down
```

## 💡 Pro Tips

1. **Better Results**: Use highest quality audio (320kbps MP3)
2. **Faster Processing**: Groq is 2-3x faster than AssemblyAI
3. **Caching**: Cache results to avoid reprocessing same songs
4. **Monitoring**: Add logging to track processing times

## 🎉 That's It!

You now have a professional audio separation service running that will dramatically improve your ChordFinder Pro accuracy!

**Questions?** Check the full documentation files or open an issue.
