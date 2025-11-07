"""
Download a small test model for Eva.
Using Phi-3-mini-4k-instruct GGUF Q4_K_M (~2.3GB)
"""
from huggingface_hub import hf_hub_download
import os

MODEL_REPO = "microsoft/Phi-3-mini-4k-instruct-gguf"
MODEL_FILE = "Phi-3-mini-4k-instruct-q4.gguf"
LOCAL_DIR = "models"

print(f"Downloading {MODEL_FILE} from {MODEL_REPO}...")
print(f"This will download ~2.3GB to {LOCAL_DIR}/")
print()

try:
    model_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir=LOCAL_DIR,
        local_dir_use_symlinks=False
    )
    print(f"\n[SUCCESS] Model downloaded successfully!")
    print(f"Location: {model_path}")
    print(f"\nTo use this model, update your .env file:")
    print(f"MODEL_PATH={os.path.abspath(model_path)}")
except Exception as e:
    print(f"\n[ERROR] Download failed: {e}")
    print("\nAlternatives:")
    print("1. Download manually from: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf")
    print("2. Use a different model from: https://huggingface.co/models?library=gguf")
    print("3. Download via LM Studio or Ollama")
