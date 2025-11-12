package com.chordfinder.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * Client service for the Python Audio Separator Microservice
 * Handles communication with the Python service for audio separation,
 * transcription, and chord detection
 */
@Service
public class AudioSeparatorClient {
    
    @Value("${audio.separator.service.url:http://localhost:5000}")
    private String serviceUrl;
    
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    
    public AudioSeparatorClient() {
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .build();
        this.objectMapper = new ObjectMapper();
    }
    
    /**
     * Process audio file - separate, transcribe, and detect chords
     * 
     * @param audioFile The audio file to process
     * @param whisperApiKey API key for Whisper service (optional)
     * @param whisperService Which service to use: "assemblyai" or "groq"
     * @return ProcessingResult with transcription and chords
     */
    public ProcessingResult processAudio(File audioFile, String whisperApiKey, 
                                        String whisperService) throws Exception {
        
        // Build multipart request
        String boundary = "----Boundary" + System.currentTimeMillis();
        byte[] requestBody = buildMultipartBody(audioFile, whisperApiKey, 
                                                whisperService, boundary);
        
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(serviceUrl + "/process-audio"))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .timeout(Duration.ofMinutes(10)) // Long timeout for processing
                .POST(HttpRequest.BodyPublishers.ofByteArray(requestBody))
                .build();
        
        HttpResponse<String> response = httpClient.send(request, 
                HttpResponse.BodyHandlers.ofString());
        
        if (response.statusCode() != 200) {
            throw new RuntimeException("Audio processing failed: " + response.body());
        }
        
        // Parse response
        return parseProcessingResult(response.body());
    }
    
    /**
     * Check if the microservice is healthy
     */
    public boolean isHealthy() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(serviceUrl + "/health"))
                    .timeout(Duration.ofSeconds(5))
                    .GET()
                    .build();
            
            HttpResponse<String> response = httpClient.send(request, 
                    HttpResponse.BodyHandlers.ofString());
            
            return response.statusCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }
    
    private byte[] buildMultipartBody(File audioFile, String whisperApiKey, 
                                     String whisperService, String boundary) throws IOException {
        StringBuilder sb = new StringBuilder();
        
        // Add audio file
        sb.append("--").append(boundary).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"audio\"; filename=\"")
          .append(audioFile.getName()).append("\"\r\n");
        sb.append("Content-Type: audio/mpeg\r\n\r\n");
        
        byte[] fileBytes = Files.readAllBytes(audioFile.toPath());
        byte[] headerBytes = sb.toString().getBytes();
        
        // Add API key if provided
        byte[] keyBytes = new byte[0];
        if (whisperApiKey != null && !whisperApiKey.isEmpty()) {
            String keyPart = "\r\n--" + boundary + "\r\n" +
                    "Content-Disposition: form-data; name=\"whisper_api_key\"\r\n\r\n" +
                    whisperApiKey;
            keyBytes = keyPart.getBytes();
        }
        
        // Add service selection
        String servicePart = "\r\n--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"whisper_service\"\r\n\r\n" +
                (whisperService != null ? whisperService : "assemblyai");
        byte[] serviceBytes = servicePart.getBytes();
        
        // End boundary
        String endBoundary = "\r\n--" + boundary + "--\r\n";
        byte[] endBytes = endBoundary.getBytes();
        
        // Combine all parts
        byte[] result = new byte[headerBytes.length + fileBytes.length + 
                                keyBytes.length + serviceBytes.length + endBytes.length];
        int pos = 0;
        System.arraycopy(headerBytes, 0, result, pos, headerBytes.length);
        pos += headerBytes.length;
        System.arraycopy(fileBytes, 0, result, pos, fileBytes.length);
        pos += fileBytes.length;
        System.arraycopy(keyBytes, 0, result, pos, keyBytes.length);
        pos += keyBytes.length;
        System.arraycopy(serviceBytes, 0, result, pos, serviceBytes.length);
        pos += serviceBytes.length;
        System.arraycopy(endBytes, 0, result, pos, endBytes.length);
        
        return result;
    }
    
    private ProcessingResult parseProcessingResult(String jsonResponse) throws IOException {
        JsonNode root = objectMapper.readTree(jsonResponse);
        
        ProcessingResult result = new ProcessingResult();
        result.setSuccess(root.get("success").asBoolean());
        
        // Parse transcription
        if (root.has("transcription") && !root.get("transcription").isNull()) {
            JsonNode transcription = root.get("transcription");
            result.setTranscriptionText(transcription.get("text").asText());
            
            // Parse words with timestamps
            if (transcription.has("words")) {
                List<WordTimestamp> words = new ArrayList<>();
                for (JsonNode word : transcription.get("words")) {
                    WordTimestamp wt = new WordTimestamp();
                    wt.setText(word.get("text").asText());
                    wt.setStart(word.get("start").asDouble());
                    wt.setEnd(word.get("end").asDouble());
                    wt.setConfidence(word.get("confidence").asDouble());
                    words.add(wt);
                }
                result.setWords(words);
            }
        }
        
        // Parse chords
        if (root.has("chords")) {
            List<ChordDetection> chords = new ArrayList<>();
            for (JsonNode chord : root.get("chords")) {
                ChordDetection cd = new ChordDetection();
                cd.setTime(chord.get("time").asDouble());
                cd.setChord(chord.get("chord").asText());
                cd.setConfidence(chord.get("confidence").asDouble());
                if (chord.has("duration")) {
                    cd.setDuration(chord.get("duration").asDouble());
                }
                chords.add(cd);
            }
            result.setChords(chords);
        }
        
        // Parse metadata
        if (root.has("metadata")) {
            JsonNode metadata = root.get("metadata");
            result.setDuration(metadata.get("duration").asDouble());
            result.setSampleRate(metadata.get("sample_rate").asInt());
        }
        
        return result;
    }
    
    // Data classes
    public static class ProcessingResult {
        private boolean success;
        private String transcriptionText;
        private List<WordTimestamp> words;
        private List<ChordDetection> chords;
        private double duration;
        private int sampleRate;
        
        // Getters and setters
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        
        public String getTranscriptionText() { return transcriptionText; }
        public void setTranscriptionText(String text) { this.transcriptionText = text; }
        
        public List<WordTimestamp> getWords() { return words; }
        public void setWords(List<WordTimestamp> words) { this.words = words; }
        
        public List<ChordDetection> getChords() { return chords; }
        public void setChords(List<ChordDetection> chords) { this.chords = chords; }
        
        public double getDuration() { return duration; }
        public void setDuration(double duration) { this.duration = duration; }
        
        public int getSampleRate() { return sampleRate; }
        public void setSampleRate(int sampleRate) { this.sampleRate = sampleRate; }
    }
    
    public static class WordTimestamp {
        private String text;
        private double start;
        private double end;
        private double confidence;
        
        // Getters and setters
        public String getText() { return text; }
        public void setText(String text) { this.text = text; }
        
        public double getStart() { return start; }
        public void setStart(double start) { this.start = start; }
        
        public double getEnd() { return end; }
        public void setEnd(double end) { this.end = end; }
        
        public double getConfidence() { return confidence; }
        public void setConfidence(double confidence) { this.confidence = confidence; }
    }
    
    public static class ChordDetection {
        private double time;
        private String chord;
        private double confidence;
        private double duration;
        
        // Getters and setters
        public double getTime() { return time; }
        public void setTime(double time) { this.time = time; }
        
        public String getChord() { return chord; }
        public void setChord(String chord) { this.chord = chord; }
        
        public double getConfidence() { return confidence; }
        public void setConfidence(double confidence) { this.confidence = confidence; }
        
        public double getDuration() { return duration; }
        public void setDuration(double duration) { this.duration = duration; }
    }
}
