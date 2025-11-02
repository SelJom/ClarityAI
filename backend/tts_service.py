import os
from google.cloud import texttospeech

try:
    tts_client = texttospeech.TextToSpeechClient()
    print("TTS Client initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Cloud TTS client: {e}")
    tts_client = None

def generate_tts_bytes(text_to_synthesize: str) -> bytes | None:
    """
    Generates audio (MP3) bytes from SIMPLE TEXT.
    This is called from main.py
    """
    if not tts_client:
        print("TTS client is not initialized.")
        return None

    try:
        # We use simple text, not SSML, to match our streaming AI
        synthesis_input = texttospeech.SynthesisInput(text=text_to_synthesize)

        # We can keep your teammate's custom voice settings
        voice = texttospeech.VoiceSelectionParams(
            language_code="fr-FR",
            name="fr-FR-Neural2-C",  
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            effects_profile_id=["headphone-class-device"]
        )

        print(f"Synthesizing speech for: '{text_to_synthesize[:30]}...'")
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        print(f'✅ Audio generated ({len(response.audio_content)} bytes)')
        return response.audio_content

    except Exception as e:
        print(f"Error during TTS generation: {e}")
        return None