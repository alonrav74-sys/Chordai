# ChordFinder Pro Integration Guide

## Overview

This guide shows how to integrate the Audio Separator Microservice into your ChordFinder Pro application.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ChordFinder Pro (Java)                      │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │   YouTube    │  │   RapidAPI   │  │  AudioSeparator     │   │
│  │     UI       │→ │   Download   │→ │      Client         │───┼──┐
│  └──────────────┘  └──────────────┘  └─────────────────────┘   │  │
│                                              ↑                    │  │
│                                              │                    │  │
│                                      ┌───────┴──────────┐        │  │
│                                      │   Display with   │        │  │
│                                      │  Synced Lyrics   │        │  │
│                                      │   and Chords     │        │  │
│                                      └──────────────────┘        │  │
└─────────────────────────────────────────────────────────────────┘  │
                                                                       │
                                                                       │ HTTP
┌─────────────────────────────────────────────────────────────────┐  │
│              Audio Separator Microservice (Python)               │◄─┘
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │   Spleeter   │  │   Whisper    │  │     Librosa         │   │
│  │  Separation  │→ │  (Assembly/  │  │  Chord Detection    │   │
│  │              │  │    Groq)     │  │                     │   │
│  └──────────────┘  └──────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Integration

### Step 1: Deploy the Microservice

#### Option A: Docker (Recommended)
```bash
cd audio-separator-service
cp .env.example .env
# Edit .env with your API keys
./start.sh
```

#### Option B: Cloud Deployment
Deploy to:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- Heroku
- Railway.app

### Step 2: Add Java Client to Your Project

#### Maven Dependencies (pom.xml)
```xml
<dependencies>
    <!-- For HTTP client -->
    <dependency>
        <groupId>org.apache.httpcomponents.client5</groupId>
        <artifactId>httpclient5</artifactId>
        <version>5.2.1</version>
    </dependency>
    
    <!-- For JSON parsing -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
        <version>2.15.2</version>
    </dependency>
</dependencies>
```

#### Copy Client Class
```bash
cp audio-separator-service/java-client/AudioSeparatorClient.java \
   src/main/java/com/chordfinder/service/
```

### Step 3: Configure Application

#### application.properties
```properties
# Audio Separator Service
audio.separator.service.url=http://localhost:5000

# API Keys (better to use environment variables)
whisper.api.key=${WHISPER_API_KEY}
whisper.service=assemblyai
```

### Step 4: Modify Your Existing Code

#### Before (Current ChordFinder Pro):
```java
@Service
public class YouTubeProcessingService {
    
    public ProcessedSong processSong(String youtubeUrl) {
        // 1. Download audio from YouTube (RapidAPI)
        File audioFile = rapidApiClient.downloadAudio(youtubeUrl);
        
        // 2. Detect chords from full audio
        List<Chord> chords = chordDetector.detect(audioFile);
        
        // 3. Transcribe lyrics from full audio (mixed with music)
        String lyrics = whisperClient.transcribe(audioFile);
        
        // Problem: Transcription quality suffers due to background music!
        
        return new ProcessedSong(chords, lyrics);
    }
}
```

#### After (With Microservice):
```java
@Service
public class YouTubeProcessingService {
    
    @Autowired
    private AudioSeparatorClient audioSeparatorClient;
    
    @Value("${whisper.api.key}")
    private String whisperApiKey;
    
    @Value("${whisper.service}")
    private String whisperService;
    
    public ProcessedSong processSong(String youtubeUrl) {
        // 1. Download audio from YouTube (same as before)
        File audioFile = rapidApiClient.downloadAudio(youtubeUrl);
        
        // 2. Send to microservice for separation + processing
        ProcessingResult result = audioSeparatorClient.processAudio(
            audioFile,
            whisperApiKey,
            whisperService
        );
        
        // 3. Extract results
        List<Chord> chords = convertChords(result.getChords());
        String lyrics = result.getTranscriptionText();
        List<LyricWord> syncedLyrics = convertWords(result.getWords());
        
        // Now you have clean separation:
        // - Chords detected from music only (more accurate!)
        // - Lyrics transcribed from vocals only (much clearer!)
        // - Word-level timestamps for perfect sync!
        
        return new ProcessedSong(chords, lyrics, syncedLyrics);
    }
    
    private List<Chord> convertChords(List<ChordDetection> detections) {
        return detections.stream()
            .map(d -> new Chord(
                d.getChord(), 
                d.getTime(), 
                d.getDuration(), 
                d.getConfidence()
            ))
            .collect(Collectors.toList());
    }
    
    private List<LyricWord> convertWords(List<WordTimestamp> words) {
        return words.stream()
            .map(w -> new LyricWord(
                w.getText(),
                w.getStart(),
                w.getEnd(),
                w.getConfidence()
            ))
            .collect(Collectors.toList());
    }
}
```

### Step 5: Update Your Frontend

#### JavaScript for Synchronized Display
```javascript
class ChordLyricsDisplay {
    constructor(processingResult) {
        this.words = processingResult.words;
        this.chords = processingResult.chords;
        this.currentWordIndex = 0;
        this.currentChordIndex = 0;
    }
    
    // Call this every animation frame with current playback time
    updateDisplay(currentTime) {
        // Update current word
        while (this.currentWordIndex < this.words.length) {
            const word = this.words[this.currentWordIndex];
            if (currentTime >= word.start && currentTime <= word.end) {
                this.highlightWord(word);
                break;
            }
            if (currentTime > word.end) {
                this.currentWordIndex++;
            } else {
                break;
            }
        }
        
        // Update current chord
        while (this.currentChordIndex < this.chords.length) {
            const chord = this.chords[this.currentChordIndex];
            const nextChord = this.chords[this.currentChordIndex + 1];
            
            if (currentTime >= chord.time && 
                (!nextChord || currentTime < nextChord.time)) {
                this.displayChord(chord);
                break;
            }
            if (nextChord && currentTime >= nextChord.time) {
                this.currentChordIndex++;
            } else {
                break;
            }
        }
    }
    
    highlightWord(word) {
        // Highlight the current word in your UI
        document.getElementById(`word-${word.id}`).classList.add('active');
    }
    
    displayChord(chord) {
        // Display the current chord
        document.getElementById('current-chord').textContent = chord.chord;
        
        // Show chord diagram if needed
        this.showChordDiagram(chord.chord);
    }
}
```

### Step 6: Enhanced Features You Can Now Build

#### 1. Karaoke Mode
```java
public void generateKaraokeView(ProcessingResult result) {
    // Create timeline with both chords and highlighted lyrics
    for (WordTimestamp word : result.getWords()) {
        // Find which chord is active at this word's time
        ChordDetection activeChord = findChordAtTime(
            result.getChords(), 
            word.getStart()
        );
        
        // Display: [C] word [G] next [Am] word...
    }
}
```

#### 2. Sheet Music Generation
```java
public SheetMusic generateSheetMusic(ProcessingResult result) {
    SheetMusicBuilder builder = new SheetMusicBuilder();
    
    // Add chords to sheet music
    for (ChordDetection chord : result.getChords()) {
        builder.addChord(chord.getChord(), chord.getTime());
    }
    
    // Add lyrics aligned to chords
    for (WordTimestamp word : result.getWords()) {
        builder.addLyric(word.getText(), word.getStart());
    }
    
    return builder.build();
}
```

#### 3. Guitar Tablature
```java
public Tablature generateTab(ProcessingResult result) {
    TablatureGenerator gen = new TablatureGenerator();
    
    // Generate fingering positions for each chord
    for (ChordDetection chord : result.getChords()) {
        TabPosition position = gen.getPosition(chord.getChord());
        gen.addToTimeline(position, chord.getTime());
    }
    
    return gen.getTab();
}
```

## Testing

### 1. Test Microservice Health
```bash
curl http://localhost:5000/health
```

### 2. Test with Sample Audio
```bash
python test_client.py process sample.mp3 YOUR_API_KEY assemblyai
```

### 3. Test Java Integration
```java
@SpringBootTest
public class AudioSeparatorIntegrationTest {
    
    @Autowired
    private AudioSeparatorClient client;
    
    @Test
    public void testProcessing() {
        assertTrue(client.isHealthy());
        
        File testFile = new File("src/test/resources/sample.mp3");
        ProcessingResult result = client.processAudio(
            testFile, 
            apiKey, 
            "assemblyai"
        );
        
        assertTrue(result.isSuccess());
        assertNotNull(result.getTranscriptionText());
        assertFalse(result.getChords().isEmpty());
    }
}
```

## Performance Optimization

### 1. Caching
```java
@Cacheable(value = "processedSongs", key = "#youtubeUrl")
public ProcessedSong processSong(String youtubeUrl) {
    // Cache results to avoid reprocessing
}
```

### 2. Async Processing
```java
@Async
public CompletableFuture<ProcessingResult> processAsync(File audioFile) {
    return CompletableFuture.supplyAsync(() -> 
        audioSeparatorClient.processAudio(audioFile, apiKey, service)
    );
}
```

### 3. Progress Tracking
```java
// Add WebSocket for real-time progress updates
@MessageMapping("/process-progress")
public void trackProgress(String sessionId) {
    // Poll microservice or implement webhook
}
```

## Deployment Checklist

- [ ] Microservice deployed and accessible
- [ ] Health check returns 200
- [ ] API keys configured in environment
- [ ] Java client integrated
- [ ] Frontend updated with sync display
- [ ] Error handling implemented
- [ ] Caching configured
- [ ] Monitoring/logging set up
- [ ] Load testing completed
- [ ] Documentation updated

## Common Issues

### Issue: Transcription quality still poor
**Solution**: Check that vocals separation worked well. Try adjusting Spleeter parameters.

### Issue: Chord detection misses some chords
**Solution**: Lower `min_confidence` threshold in ChordDetector or use better audio quality.

### Issue: Timing sync is off
**Solution**: Ensure audio timestamps are correctly converted between different sample rates.

### Issue: Service timeout
**Solution**: Increase timeout values or optimize audio file size before sending.

## Next Steps

1. ✅ Deploy microservice
2. ✅ Integrate Java client
3. ✅ Update frontend sync
4. 🎯 Test with real YouTube videos
5. 🎯 Add error handling
6. 🎯 Implement caching
7. 🎯 Add user feedback
8. 🎯 Monitor performance

## Support

- Microservice logs: `docker-compose logs -f`
- Java client issues: Check network connectivity to microservice
- API rate limits: Monitor AssemblyAI/Groq dashboards
