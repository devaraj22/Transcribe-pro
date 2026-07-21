import json
import os

candidates = [
    os.path.expanduser("~/.ollama/models"),
    "/usr/share/ollama/.ollama/models",
]
ollama_dir = next((d for d in candidates if os.path.isdir(d)), None)

if not ollama_dir:
    print("Could not find an Ollama models directory automatically.")
    print("Run: sudo find / -xdev -type d -name manifests 2>/dev/null")
else:
    manifest = os.path.join(ollama_dir, "manifests/registry.ollama.ai/library/qwen3/8b")
    if not os.path.exists(manifest):
        print("Manifest not found at:", manifest)
        print("Contents of manifests dir:")
        for root, dirs, files in os.walk(os.path.join(ollama_dir, "manifests")):
            for f in files:
                print(" ", os.path.join(root, f))
    else:
        with open(manifest) as f:
            m = json.load(f)
        for layer in m["layers"]:
            if layer["mediaType"] == "application/vnd.ollama.image.model":
                digest = layer["digest"].replace(":", "-")
                blob_path = os.path.join(ollama_dir, "blobs", digest)
                if os.path.exists(blob_path):
                    size_gb = os.path.getsize(blob_path) / (1024 ** 3)
                    print(f"Found it ({size_gb:.1f} GB):")
                    print("LOCAL_LLM_MODEL_PATH=" + blob_path)
                else:
                    print("Manifest points to a blob that does not exist:", blob_path)
                break