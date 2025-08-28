### **Important Instructions**:  
- Click on *"Use this template"* button and *"Create a new repository"* in your github account for submission.
<img width="1262" height="93" alt="Screenshot 2025-08-15 at 5 59 49 AM" src="https://github.com/user-attachments/assets/b72d5afd-ba07-4da1-ac05-a373b3168b6a" />

- Add one of the following open source licenses - [MIT](https://opensource.org/licenses/MIT), [Apache 2.0](https://opensource.org/licenses/Apache-2.0) or [BSD 3-Clause](https://opensource.org/licenses/BSD-3-Clause) to your submission repository. 
- Once your repository is ready for **evaluation** send an email to ennovatex.io@samsung.com with the subject - "AI Challenge Submission - Team name" and the body of the email must contain only the Team Name, Team Leader Name & your GitHub project repository link.
- All submission project materials outlined below must be added to the github repository and nothing should be attached in the submission email.
- In case of any query, please feel free to reach out to us at ennovatex.io@samsung.com

#### Evaluation Criteria

| Project Aspect | % |
| --- | --- |
| Novelty of Approach | 25% |
| Technical implementation & Documentation | 25% |
| UI/UX Design or User Interaction Design | 15% |
| Ethical Considerations & Scalability | 10% |
| Demo Video (10 mins max) | 25% |

**-------------------------- Your Project README.md should start from here -----------------------------**

# Samsung EnnovateX 2025 AI Challenge Submission

## Problem Statement
*Crafting the Next Generation of Human-AI Interaction on the Edge
*

## Team Name
*Code-RX*

## Team Members
- Muhammed Fadhil  
- Mohammed Zayan
- Muhammed Sameer 
 

## Demo Video Link
*(YouTube public/unlisted link — Google Drive or other uploads are not allowed)*

---

# Project Artefacts

## Technical Documentation
[Docs](docs)  
All technical details must be written in markdown files inside the `docs/` folder.

## Source Code
[Source](src)  
The source code is inside the `src/` folder and includes:
- `server/` – Python WebSocket backend for STT → LLM → Disfluency → TTS pipeline  
- `app/` – Android client (or frontend) for real-time interaction  

## Models Used
- [Vosk Small EN Model](https://alphacephei.com/vosk/models)  
- [Phi-2 LLM](https://huggingface.co/microsoft/phi-2)  
- [Disfluency Adder (T5-based)](https://huggingface.co/)  
- [Coqui TTS](https://github.com/coqui-ai/TTS)  


---

# Attribution

This project builds on the following open-source projects:
- [Vosk Speech Recognition Toolkit](https://github.com/alphacep/vosk-api)  
- [Transformers by Hugging Face](https://github.com/huggingface/transformers)  
- [Coqui TTS](https://github.com/coqui-ai/TTS)  

### New Contributions
- End-to-end pipeline for STT → LLM → Disfluency → TTS  
- Real-time WebSocket server for low-latency client-server communication  
- Android client for audio streaming and playback  

---

# Important Instructions to run the project
1) Clone this repository
2) run the src/server/download_models.sh
3) make sure to have the following installed in your machine before proceding to the next step-
espeak-ng
node.js
4) creare a virtual environment with the following pip installs-
pip install torch
pip install transformers
pip install vosk
pip install TTS
pip install websockets
pip install soundfile
pip install numpy
5) run the server.py
6) type your network ip adress in the 43d line of the MainActivity.kt under src/app/app1
7) build the app in your android
