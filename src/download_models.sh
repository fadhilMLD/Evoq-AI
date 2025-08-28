#!/bin/bash

# Script to download and extract models for Evoq-AI
# Run this from the project root directory

MODELS_DIR="src/models"
TEMP_DIR="$MODELS_DIR/temp"


mkdir -p "$MODELS_DIR"
mkdir -p "$TEMP_DIR"

BASE_URL="https://huggingface.co/MFadhil12/Evoq-AI/resolve/main"


MODELS=(
    "disfluency_adder.zip"
    "models/phi-2-local.zip"
    "models/vosk-model-small-en-us-0.15.zip"
    "tts_models--en--ljspeech--glow-tts.zip"
)

echo "Starting model download process..."
echo "=================================="


for model in "${MODELS[@]}"; do

    filename=$(basename "$model")
    model_name="${filename%.zip}"
    
    echo "Processing: $model_name"
    

    echo "Downloading $filename..."
    wget -q --show-progress -P "$TEMP_DIR" "$BASE_URL/$model"
    
    if [ $? -eq 0 ]; then
        echo "Download completed successfully!"
        

        echo "Extracting $filename..."
        unzip -q "$TEMP_DIR/$filename" -d "$MODELS_DIR"
        
        if [ $? -eq 0 ]; then
            echo "Extraction completed successfully!"
            

            rm "$TEMP_DIR/$filename"
            echo "Cleaned up temporary file"
        else
            echo "Error: Failed to extract $filename"
            exit 1
        fi
        
        echo "---"
    else
        echo "Error: Failed to download $filename"
        exit 1
    fi
done

rmdir "$TEMP_DIR" 2>/dev/null

echo "=================================="
echo "All models downloaded and extracted successfully!"
echo "Models are available in: $MODELS_DIR"
