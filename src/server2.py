import asyncio
import websockets
import base64
import json
import torch
import time
import requests
from vosk import Model, KaldiRecognizer
from transformers import AutoModelForCausalLM, AutoTokenizer, T5ForConditionalGeneration, T5Tokenizer, pipeline


# ----------------------------
# Load Vosk STT
# ----------------------------
stt_path = "vosk-model-small-en-us-0.15"
stt_ = Model(stt_path)
recognizer = KaldiRecognizer(stt_, 16000)
print("STT loaded successfully.")


# ----------------------------
# Load Phi-2 LLM
# ----------------------------
MODEL_DIR = "./phi-2-local"
MODEL_ID = "microsoft/phi-2"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    cache_dir=MODEL_DIR,
    torch_dtype=torch.bfloat16,
).to("cuda")
model.eval()
print("LLM loaded successfully.")


# ----------------------------
# Load Disfluency Adder (T5)
# ----------------------------
disfluency_model = T5ForConditionalGeneration.from_pretrained("./disfluency_adder")
disfluency_tokenizer = T5Tokenizer.from_pretrained("./disfluency_adder", legacy=False)

disfluency_adder = pipeline(
    "text2text-generation",
    model=disfluency_model,
    tokenizer=disfluency_tokenizer,
    device=0 if torch.cuda.is_available() else -1
)
print("Disfluency adder loaded successfully.")


# ----------------------------
# Inworld TTS Setup
# ----------------------------
API_KEY = "Q0lNRGgwUmdSTGQ1a0RtcmdkbDJjV09NVmhYeWhCekI6MnVjSlY5V3F3RFB3cXcyVzF2aGVIelJDV3NxNlVBcHJQYzBNNXU0TTZUZlpvMkF2bllIM0VrMXBkQUJQYUNJQg=="
TTS_URL = "https://api.inworld.ai/tts/v1/voice"
TTS_HEADERS = {
    "Authorization": f"Basic {API_KEY}",
    "Content-Type": "application/json"
}
VOICE_ID = "Craig"
MODEL_ID = "inworld-tts-1"


def synthesize_speech(text: str) -> bytes:
    """Send text to Inworld TTS API and return MP3 bytes."""
    payload = {
        "text": text,
        "voiceId": VOICE_ID,
        "modelId": MODEL_ID
    }
    response = requests.post(TTS_URL, json=payload, headers=TTS_HEADERS)
    response.raise_for_status()
    result = response.json()
    return base64.b64decode(result["audioContent"])


# ----------------------------
# Conversation setup
# ----------------------------
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
    # Build a fresh prompt each time, without history
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


# ----------------------------
# WebSocket handler
# ----------------------------
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

                        # Step 1: Generate reply from LLM
                        reply, llm_time = generate_response(text)
                        print(f"LLM reply: {reply} (LLM: {llm_time}s)")

                        # Step 2: Add disfluencies
                        disfluent_reply, disfluency_time = add_disfluencies(reply)
                        print(f"Final reply: {disfluent_reply} (Disfluency: {disfluency_time}s)")

                        # Step 3: Convert to speech
                        audio_out = synthesize_speech(disfluent_reply)
                        print(f"TTS generated {len(audio_out)} bytes of audio")

                        # Step 4: Send audio back to client (base64)
                        await websocket.send("AUDIO:" + base64.b64encode(audio_out).decode("utf-8"))

            else:
                print("Received non-audio message:", message)

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Client disconnected: {e}")


# ----------------------------
# Main
# ----------------------------
async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Server started at ws://0.0.0.0:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
