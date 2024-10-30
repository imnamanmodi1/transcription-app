from flask import Flask, request, jsonify
import whisper
import os
import time
import tempfile
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Load Whisper model
model = whisper.load_model("base")

# Create a ThreadPoolExecutor for handling transcription tasks
executor = ThreadPoolExecutor(max_workers=4)  # Increase workers to process chunks in parallel

def split_audio(filepath, chunk_length_ms=60000):
    """Splits audio file into chunks of specified length (in milliseconds)."""
    audio = AudioSegment.from_file(filepath)
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    chunk_paths = []

    for i, chunk in enumerate(chunks):
        chunk_path = f"/tmp/chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunk_paths.append(chunk_path)

    return chunk_paths

def transcribe_chunk(chunk_path):
    """Transcribes a single audio chunk."""
    result = model.transcribe(chunk_path)
    os.remove(chunk_path)  # Remove chunk file after processing
    return result["text"]

def transcribe_file(filepath):
    """Handles the transcription process by splitting into chunks, transcribing in parallel, and combining results."""
    try:
        # Start transcription timer
        transcribe_start = time.time()

        # Split audio into chunks
        chunk_paths = split_audio(filepath)

        # Transcribe chunks in parallel
        with ThreadPoolExecutor(max_workers=4) as chunk_executor:
            futures = [chunk_executor.submit(transcribe_chunk, chunk) for chunk in chunk_paths]
            results = [future.result() for future in futures]

        # Combine transcriptions from all chunks
        full_transcription = " ".join(results)

        # End transcription timer
        transcribe_end = time.time()

        # Get the size of the file
        file_size = os.path.getsize(filepath)

        # Prepare the result
        transcription_result = {
            "transcription": full_transcription,
            "stats": {
                "total_processing_time": transcribe_end - transcribe_start,
                "words_per_second": round(len(full_transcription) / (transcribe_end - transcribe_start), 2),
                "file_size_in_bytes": file_size
            }
        }
    finally:
        # Ensure file is removed after processing
        os.remove(filepath)

    return transcription_result

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        # Save the file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(temp_file.name)

        # Start the transcription task asynchronously
        future = executor.submit(transcribe_file, temp_file.name)
        result = future.result()

        # Return the result to the client
        return jsonify(result)

    return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
