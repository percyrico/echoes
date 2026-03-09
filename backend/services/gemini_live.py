"""Gemini Live session manager for Echoes — real-time voice narration."""

import asyncio
import base64
import sys
from typing import Optional

from google import genai
from google.genai import types

from models.schemas import Scenario


def _log(msg: str):
    print(msg, flush=True)


class GeminiLiveSession:
    """Manages a Gemini Live API session for real-time voice mystery narration."""

    def __init__(self, scenario: Scenario, api_key: str):
        self.scenario = scenario
        self.client = genai.Client(api_key=api_key)
        self.session = None
        self._live_ctx = None
        self._running = False
        self.ready = asyncio.Event()

    async def connect(self, system_prompt: str):
        """Establish a Gemini Live session with the given system prompt."""
        _log("[GeminiLive] Connecting...")
        live_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon",
                    )
                )
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=types.Content(
                parts=[
                    types.Part(text="VOICE DIRECTION: Speak slowly, clearly, and deliberately. Pause briefly between sentences for dramatic effect. Enunciate every word. Do not rush.\n\n" + system_prompt)
                ]
            ),
        )

        self._live_ctx = self.client.aio.live.connect(
            model="gemini-2.5-flash-native-audio-latest",
            config=live_config,
        )
        self.session = await self._live_ctx.__aenter__()
        self._running = True
        self.ready.set()
        _log("[GeminiLive] Connected and ready!")

    async def send_audio(self, audio_data: bytes):
        """Send audio chunk to Gemini Live."""
        if not self.session:
            return
        await self.session.send_realtime_input(
            audio=types.Blob(
                data=audio_data,
                mime_type="audio/pcm;rate=16000",
            )
        )

    async def send_text(self, text: str):
        """Send a text message to the live session."""
        if not self.ready.is_set():
            _log(f"[GeminiLive] Waiting for session to be ready before sending text...")
            try:
                await asyncio.wait_for(self.ready.wait(), timeout=15)
            except asyncio.TimeoutError:
                _log(f"[GeminiLive] Timeout waiting for session — cannot send text")
                return

        if self.session:
            _log(f"[GeminiLive] Sending text: {text[:80]}...")
            _log(f"[GeminiLive] Session alive: {self.session is not None}, running: {self._running}")
            try:
                await self.session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=text)],
                    ),
                    turn_complete=True,
                )
                _log(f"[GeminiLive] Text sent successfully — awaiting model response...")
            except Exception as e:
                _log(f"[GeminiLive] SEND TEXT FAILED: {e}")
                import traceback
                traceback.print_exc()
        else:
            _log(f"[GeminiLive] No session — cannot send text (running={self._running})")

    async def receive_responses(self, callback):
        """Listen for responses from Gemini Live and forward via callback.

        Uses manual async iteration with timeouts for diagnostics.
        Keeps listening across multiple turns until disconnected.
        """
        if not self.session:
            _log("[GeminiLive] No session for receive_responses")
            return

        _log("[GeminiLive] Starting receive loop...")
        response_count = 0
        turn_count = 0

        try:
            gen = self.session.receive()
            while self._running:
                try:
                    # Wait up to 120s for next message — log heartbeat on timeout
                    try:
                        response = await asyncio.wait_for(gen.__anext__(), timeout=120)
                    except asyncio.TimeoutError:
                        _log(f"[GeminiLive] Still waiting for response (turns so far: {turn_count})...")
                        continue
                    except StopAsyncIteration:
                        _log(f"[GeminiLive] Receive generator ended after turn {turn_count}. Creating new generator...")
                        await asyncio.sleep(0.2)
                        gen = self.session.receive()
                        continue

                    # Process the response
                    server_content = getattr(response, 'server_content', None)
                    if not server_content:
                        _log(f"[GeminiLive] Non-content response: {type(response).__name__}")
                        continue

                    response_count += 1

                    # Handle audio output transcription
                    if server_content.output_transcription:
                        transcription = server_content.output_transcription
                        if transcription.text:
                            await callback({
                                "type": "text",
                                "data": transcription.text,
                            })

                    # Handle model turn parts (audio data)
                    if server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            if part.inline_data:
                                audio_b64 = base64.b64encode(
                                    part.inline_data.data
                                ).decode("utf-8")
                                await callback({
                                    "type": "audio",
                                    "data": audio_b64,
                                    "mime_type": part.inline_data.mime_type,
                                })

                    if server_content.turn_complete:
                        turn_count += 1
                        _log(f"[GeminiLive] Turn {turn_count} complete ({response_count} chunks). Waiting for next input...")
                        await callback({"type": "turn_complete"})

                except Exception as inner_err:
                    err_str = str(inner_err)
                    if "cancel" in err_str.lower():
                        raise
                    # If the connection closed (1000 OK), stop the loop
                    if "1000" in err_str or "ConnectionClosed" in type(inner_err).__name__:
                        _log(f"[GeminiLive] Session closed by server (1000 OK). Stopping receive loop.")
                        break
                    _log(f"[GeminiLive] Inner receive error: {inner_err}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            _log("[GeminiLive] Receive loop cancelled")
            raise
        except Exception as e:
            _log(f"[GeminiLive] Receive error: {e}")
            import traceback
            traceback.print_exc()
            await callback({"type": "error", "data": str(e)})

    async def disconnect(self):
        """Close the Gemini Live session."""
        _log("[GeminiLive] Disconnecting...")
        self._running = False
        if self.session and self._live_ctx:
            try:
                await self._live_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            self.session = None
            self._live_ctx = None
        _log("[GeminiLive] Disconnected")
