"""
skills/camera.py — Webcam capture + Ollama vision.
"""

import base64
import cv2
from skills.base import BaseSkill


class CameraSkill(BaseSkill):
    name = "camera"
    description = "Capture a photo from the webcam and describe what's visible using vision AI."
    schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["look"],
                "description": "Camera action.",
            },
            "question": {
                "type": "string",
                "description": "What to ask about the image.",
            },
        },
        "required": ["command"],
    }

    def __init__(self, llm=None, device_index: int = 0):
        self._llm = llm
        self._device_index = device_index

    def execute(self, params: dict) -> str:
        question = params.get("question", "What do you see?")
        image_b64 = self._capture()
        if not image_b64:
            return "Couldn't access the camera."
        if not self._llm:
            return "Vision LLM not available."
        try:
            prompt = (f"The user pointed their camera and asked: '{question}'. "
                      f"Describe what you see in ONE concise sentence.")
            return self._llm.chat([], prompt, image_b64=image_b64)
        except Exception as e:
            return f"Vision analysis failed: {e}"

    def _capture(self) -> str | None:
        cap = cv2.VideoCapture(self._device_index)
        if not cap.isOpened():
            return None
        try:
            for _ in range(15):
                cap.read()
            ret, frame = cap.read()
            if not ret or frame is None:
                return None
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(buf).decode("utf-8")
        finally:
            cap.release()
