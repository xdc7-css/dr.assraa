# Third-Party Notices and Open-Source Attributions

This project integrates multiple open-source software libraries, pretrained neural model weights, and speech assets. In compliance with open-source licensing standards and academic integrity, each third-party component is attributed below with its official provenance and specific license.

---

## 1. Computer Vision & Object Detection
- **Component:** YOLO11 (You Only Look Once, Version 11)
- **Model Checkpoint:** `yolo11n.pt` (Nano variant)
- **Source Repository:** [Ultralytics GitHub](https://github.com/ultralytics/ultralytics)
- **Official Documentation:** [Ultralytics YOLO11 Docs](https://docs.ultralytics.com/models/yolo11/)
- **License:** **AGPL-3.0** (GNU Affero General Public License v3.0)
- **Attribution:** Glenn Jocher and the Ultralytics Team.
- **Notice:** Ultralytics open-source software is licensed under AGPL-3.0. Commercial use outside open-source licensing requires an enterprise license from Ultralytics.

---

## 2. Optical Character Recognition (OCR)
- **Component:** EasyOCR
- **Model Checkpoints:** CRAFT text detector (`craft_mlt_25k.pth`) and Arabic/Latin character recognizers (`arabic.pth`, `latin.pth`).
- **Source Repository:** [JaidedAI EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR)
- **Official Documentation:** [Jaided AI Documentation](https://www.jaided.ai/easyocr/)
- **License:** **Apache-2.0**
- **Attribution:** Jaided AI and contributors.
- **Notice:** CRAFT text detector was originally developed by Clova AI, NAVER Corp, and is utilized within EasyOCR under Apache-2.0.

---

## 3. Automatic Speech Recognition (ASR)
- **Component:** faster-whisper
- **Model Checkpoint:** `Systran/faster-whisper-base` (Multilingual Base, CTranslate2 INT8)
- **Source Repository:** [SYSTRAN faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- **Model Card:** [Hugging Face Systran/faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base)
- **Original Architecture:** OpenAI Whisper ([OpenAI Whisper GitHub](https://github.com/openai/whisper))
- **Engine:** CTranslate2 by OpenNMT ([CTranslate2 GitHub](https://github.com/OpenNMT/CTranslate2))
- **License:** **MIT License**
- **Attribution:** Guillaume Klein, SYSTRAN, and OpenAI.

---

## 4. Speech Synthesis (Text-to-Speech)
- **Component:** Piper TTS Engine
- **Engine Repository:** [OHF-Voice Piper GitHub](https://github.com/OHF-Voice/piper1-gpl)
- **Engine License:** **GPL-3.0** (GNU General Public License v3.0)
- **Voice Checkpoint:** `ar_JO-kareem-medium` (`ar_JO-kareem-medium.onnx` and `ar_JO-kareem-medium.onnx.json`)
- **Voice Repository:** [Rhasspy Piper Voices](https://huggingface.co/rhasspy/piper-voices/tree/main/ar/ar_JO/kareem/medium)
- **Voice Model Card:** [MODEL_CARD](https://huggingface.co/rhasspy/piper-voices/blob/main/ar/ar_JO/kareem/medium/MODEL_CARD)
- **Voice License / Provenance:** Trained on Arabic speech data by Kareem / Rhasspy community. License defined in the voice model card.
- **Notice:** The Piper runtime engine is GPL-3.0. Combined binary distributions incorporating Piper must honor GPL-3.0 terms.

---

## 5. Vision-Language Model (VLM)
- **Component:** Qwen3-VL 2B
- **Runtime:** Ollama Windows Engine v0.40.11 ([Ollama Website](https://ollama.com/))
- **Engine License:** MIT License (Ollama / llama.cpp backend)
- **Ollama Library Tag:** `qwen3-vl:2b` ([Ollama Library: qwen3-vl](https://ollama.com/library/qwen3-vl:2b))
- **Verified Checkpoint Digest:** `0635d9d857d497aeadba3d7d27485746c50554446f9f6ec01ef39788221adbe8`
- **Original Model Checkpoint:** `Qwen/Qwen3-VL-2B-Instruct` ([Hugging Face](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct))
- **Original Repository:** [QwenLM GitHub](https://github.com/QwenLM/Qwen3-VL)
- **License:** **Apache-2.0** (Qwen Community License / Apache 2.0 per model card)
- **Attribution:** Alibaba Cloud Qwen Team.

---

## 6. Backend and Web Frameworks
- **FastAPI:** MIT License, Sebastián Ramírez ([FastAPI GitHub](https://github.com/tiangolo/fastapi))
- **Uvicorn:** BSD-3-Clause License, Encode ([Uvicorn GitHub](https://github.com/encode/uvicorn))
- **PyTorch & TorchVision:** BSD-style License, Meta AI / PyTorch Contributors ([PyTorch GitHub](https://github.com/pytorch/pytorch))
- **OpenCV (opencv-python):** Apache-2.0 License, OpenCV Team ([OpenCV GitHub](https://github.com/opencv/opencv))
- **Pillow (PIL):** HPND License, Alex Clark and Contributors ([Pillow GitHub](https://github.com/python-pillow/Pillow))
- **jiwer:** Apache-2.0 License, Nik Vaessen ([jiwer GitHub](https://github.com/jitsi/jiwer))
- **Google Fonts (Cairo, Outfit):** SIL Open Font License 1.1 ([Google Fonts](https://fonts.google.com/))
