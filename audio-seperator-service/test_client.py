#!/usr/bin/env python3
"""
Test client for Audio Separator Service
"""

import requests
import sys
import os
import json

SERVICE_URL = os.environ.get('SERVICE_URL', 'http://localhost:5000')

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is healthy!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return False

def test_process_audio(audio_file_path, api_key=None, service='assemblyai'):
    """Test audio processing"""
    print(f"\n🎵 Testing audio processing...")
    print(f"   File: {audio_file_path}")
    print(f"   Service: {service}")
    
    if not os.path.exists(audio_file_path):
        print(f"❌ File not found: {audio_file_path}")
        return False
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'audio': f}
            data = {}
            
            if api_key:
                data['whisper_api_key'] = api_key
            
            data['whisper_service'] = service
            
            print("   Uploading and processing (this may take a few minutes)...")
            response = requests.post(
                f"{SERVICE_URL}/process-audio",
                files=files,
                data=data,
                timeout=600  # 10 minutes timeout
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Processing complete!")
            print("\n📊 Results:")
            print(f"   Success: {result['success']}")
            
            if 'metadata' in result:
                print(f"   Duration: {result['metadata']['duration']:.2f}s")
                print(f"   Sample Rate: {result['metadata']['sample_rate']} Hz")
            
            if result.get('transcription'):
                trans = result['transcription']
                print(f"\n📝 Transcription:")
                print(f"   Text: {trans.get('text', '')[:100]}...")
                print(f"   Words: {len(trans.get('words', []))} words")
            
            if result.get('chords'):
                chords = result['chords']
                print(f"\n🎸 Chords:")
                print(f"   Detected: {len(chords)} chord changes")
                print(f"   First 5 chords:")
                for chord in chords[:5]:
                    print(f"      {chord['time']:.2f}s: {chord['chord']} "
                          f"(conf: {chord['confidence']:.2f})")
            
            # Save full result
            output_file = 'test_result.json'
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Full results saved to: {output_file}")
            
            return True
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Health check: python test_client.py health")
        print("  Process audio: python test_client.py process <audio_file> [api_key] [service]")
        print("\nExamples:")
        print("  python test_client.py health")
        print("  python test_client.py process song.mp3")
        print("  python test_client.py process song.mp3 your_api_key assemblyai")
        print("  python test_client.py process song.mp3 your_api_key groq")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'health':
        success = test_health()
    elif command == 'process':
        if len(sys.argv) < 3:
            print("❌ Please provide audio file path")
            sys.exit(1)
        
        audio_file = sys.argv[2]
        api_key = sys.argv[3] if len(sys.argv) > 3 else None
        service = sys.argv[4] if len(sys.argv) > 4 else 'assemblyai'
        
        # First check health
        if not test_health():
            print("\n❌ Service is not healthy. Please start the service first.")
            sys.exit(1)
        
        success = test_process_audio(audio_file, api_key, service)
    else:
        print(f"❌ Unknown command: {command}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
