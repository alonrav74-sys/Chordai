package com.chordfinder.example;

import com.chordfinder.service.AudioSeparatorClient;
import com.chordfinder.service.AudioSeparatorClient.ProcessingResult;
import com.chordfinder.service.AudioSeparatorClient.WordTimestamp;
import com.chordfinder.service.AudioSeparatorClient.ChordDetection;

import java.io.File;

/**
 * Example usage of the AudioSeparatorClient
 */
public class AudioProcessingExample {
    
    public static void main(String[] args) {
        AudioSeparatorClient client = new AudioSeparatorClient();
        
        // Check if service is healthy
        if (!client.isHealthy()) {
            System.err.println("Audio separator service is not available!");
            return;
        }
        
        System.out.println("Audio separator service is healthy ✓");
        
        try {
            // The audio file from RapidAPI download
            File audioFile = new File("downloaded_audio.mp3");
            
            // Your Whisper API key (AssemblyAI or Groq)
            String apiKey = "your_api_key_here";
            String service = "assemblyai"; // or "groq"
            
            System.out.println("Processing audio file: " + audioFile.getName());
            System.out.println("This may take a few minutes...");
            
            // Process the audio
            ProcessingResult result = client.processAudio(audioFile, apiKey, service);
            
            if (!result.isSuccess()) {
                System.err.println("Processing failed!");
                return;
            }
            
            System.out.println("\n=== Processing Results ===");
            System.out.println("Duration: " + result.getDuration() + " seconds");
            System.out.println("Sample Rate: " + result.getSampleRate() + " Hz");
            
            // Display transcription
            System.out.println("\n=== Transcription ===");
            System.out.println(result.getTranscriptionText());
            
            // Display word-level timestamps (useful for lyrics sync)
            System.out.println("\n=== Word Timestamps (first 10) ===");
            int wordCount = 0;
            for (WordTimestamp word : result.getWords()) {
                if (wordCount++ >= 10) break;
                System.out.printf("[%.2f - %.2f] %s (conf: %.2f)\n", 
                    word.getStart(), word.getEnd(), word.getText(), word.getConfidence());
            }
            
            // Display chord progression
            System.out.println("\n=== Chord Progression ===");
            for (ChordDetection chord : result.getChords()) {
                System.out.printf("%.2fs: %s (conf: %.2f, duration: %.2fs)\n", 
                    chord.getTime(), chord.getChord(), 
                    chord.getConfidence(), chord.getDuration());
            }
            
            // Example: Create synchronized lyrics with chords
            System.out.println("\n=== Synchronized Lyrics & Chords ===");
            createSynchronizedOutput(result);
            
        } catch (Exception e) {
            System.err.println("Error processing audio: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Example of how to synchronize chords with lyrics
     */
    private static void createSynchronizedOutput(ProcessingResult result) {
        // This is where you can combine the word timestamps with chord changes
        // to create a synchronized display like in your ChordFinder Pro
        
        int chordIndex = 0;
        String currentChord = "N";
        
        for (WordTimestamp word : result.getWords()) {
            // Check if there's a chord change at this word's timestamp
            while (chordIndex < result.getChords().size() && 
                   result.getChords().get(chordIndex).getTime() <= word.getStart()) {
                currentChord = result.getChords().get(chordIndex).getChord();
                System.out.printf("\n[%s] ", currentChord);
                chordIndex++;
            }
            
            System.out.print(word.getText() + " ");
        }
        System.out.println();
    }
}
