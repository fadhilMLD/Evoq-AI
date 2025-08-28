import asyncio
import websockets
import base64
import json
import torch
import time
import os
from vosk import Model, KaldiRecognizer
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    T5ForConditionalGeneration,
    T5Tokenizer,
    pipeline
)
from TTS.api import TTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODELS_DIR = os.path.abspath(os.path.join(SRC_DIR, "models"))


# Loading Vosk

stt_path = os.path.join(MODELS_DIR, "vosk-model-small-en-us-0.15")
print(f"Loading Vosk STT from: {stt_path}")
stt_ = Model(stt_path)
recognizer = KaldiRecognizer(stt_, 16000)
print("STT loaded successfully.")


# Loading Phi-2 LLM

phi2_path = os.path.join(MODELS_DIR, "phi-2-local")
MODEL_ID = "microsoft/phi-2"

print(f"Loading Phi-2 from: {phi2_path}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=phi2_path)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    cache_dir=phi2_path,
    torch_dtype=torch.bfloat16,
).to("cuda" if torch.cuda.is_available() else "cpu")
model.eval()
print("LLM loaded successfully.")


# Loading Disfluency Adder
disfluency_path = os.path.join(MODELS_DIR, "disfluency_adder")

print(f"Loading Disfluency Adder from: {disfluency_path}")
disfluency_model = T5ForConditionalGeneration.from_pretrained(disfluency_path)
disfluency_tokenizer = T5Tokenizer.from_pretrained(disfluency_path, legacy=False)

disfluency_adder = pipeline(
    "text2text-generation",
    model=disfluency_model,
    tokenizer=disfluency_tokenizer,
    device=0 if torch.cuda.is_available() else -1
)
print("Disfluency adder loaded successfully.")

# Loading Coqui TTS

print("Loading Coqui TTS...")
try:
    tts = TTS(model_name="tts_models/en/ljspeech/glow-tts")
except Exception as e:
    print(f"Glow-TTS failed: {e}")
    try:
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
        print("Using Tacotron2 as fallback")
    except Exception as e2:
        print(f"All TTS methods failed: {e2}")
        raise RuntimeError("Could not load any TTS model")

print("TTS loaded successfully.")

def synthesize_speech(text: str) -> bytes:
    """Generate speech from text using Coqui TTS and return WAV bytes."""
    try:
        #temporary audio file
        wav_path = os.path.join(BASE_DIR, "temp_out.wav")
        tts.tts_to_file(text=text, file_path=wav_path)
        with open(wav_path, "rb") as f:
            audio_data = f.read()
        os.remove(wav_path)
        return audio_data
    except Exception as e:
        print(f"TTS synthesis failed: {e}")
        return b""


# Instruction for the LLM
Instruction = """
You are my closest friend talking with me on a casual phone call.
Rules:
1) Only write your spoken response after 'You:'.
2) Never write lines for 'Me:'.
3) Never repeat my words.
4) Reply naturally, like a supportive and caring friend.
5) Keep it short and conversational.
""".strip()

def generate_response(user_text: str) -> (str, float):
    """Generate a response from the LLM using only the latest user input."""
    prompt = Instruction + f"\nMe: {user_text}\nYou:"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    start = time.time()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=30,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )
    end = time.time()

    full_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    answer = full_text[len(prompt):].strip()

    if "You:" in answer:
        answer = answer.split("You:", 1)[-1].strip()
    if "\n" in answer:
        answer = answer.split("\n", 1)[0].strip()

    return answer, round(end - start, 1)

def add_disfluencies(text: str) -> (str, float):
    """Pass text through the disfluency adder model and return time taken."""
    prompt = f"add disfluencies: {text}"
    start = time.time()
    result = disfluency_adder(
        prompt,
        max_length=60,
        num_beams=3,
        temperature=0.8,
        do_sample=True,
        no_repeat_ngram_size=2
    )
    end = time.time()
    return result[0]['generated_text'], round(end - start, 1)


# WebSocket Server
async def handler(websocket):
    print("Client connected")

    try:
        async for message in websocket:
            if message.startswith("AUDIO:"):
                b64data = message.split("AUDIO:", 1)[1]
                audio_bytes = base64.b64decode(b64data)

                stt_start = time.time()
                if recognizer.AcceptWaveform(audio_bytes):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    stt_end = time.time()
                    stt_time = round(stt_end - stt_start, 1)

                    if text:
                        print(f"User said: {text} (STT: {stt_time}s)")
                        # 1: Generate LLM response
                        reply, llm_time = generate_response(text)
                        print(f"LLM reply: {reply} (LLM: {llm_time}s)")

                        # 2: Add disfluencies
                        disfluent_reply, disfluency_time = add_disfluencies(reply)
                        print(f"Final reply: {disfluent_reply} (Disfluency: {disfluency_time}s)")

                        # 3: Convert to speech
                        tts_start = time.time()
                        audio_out = synthesize_speech(disfluent_reply)
                        tts_time = round(time.time() - tts_start, 1)
                        print(f"TTS generated {len(audio_out)} bytes of audio (TTS: {tts_time}s)")

                        # 4: Send audio to client
                        await websocket.send("AUDIO:" + base64.b64encode(audio_out).decode("utf-8"))

            else:
                print("Received non-audio message:", message)

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Client disconnected: {e}")


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Server started at ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())