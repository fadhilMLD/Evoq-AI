# Technical Documentation

## Overview
This project implements a real-time conversational AI pipeline using Speech-to-Text (STT), a Large Language Model (LLM), a Disfluency Adder, and Text-to-Speech (TTS).  
The system runs on a Python WebSocket server, with clients (Android/iOS/Web) connecting to it for live conversation.

---

## System Architecture

### 1. Input
- The client records the user's voice and streams audio in small chunks to the server over WebSocket.
- Audio chunks are encoded in **Base64** and prefixed with `"AUDIO:"`.

### 2. Speech-to-Text (STT)
- The server uses **Vosk** to convert raw audio into text.
- Model used: `vosk-model-small-en-us-0.15`.

### 3. Response Generation (LLM)
- The recognized text is passed to **Phi-2 LLM** (via Hugging Face `transformers`).
- Prompt template enforces a conversational, friendly style:
