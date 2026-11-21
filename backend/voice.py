
# voice.py - Browser <-> Backend <-> Gemini Live

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai import types

from live_config import gemini, MODEL, CONFIG, answer_tool_call

router = APIRouter()


@router.websocket("/voice")
async def voice(ws: WebSocket):

    await ws.accept()

    try:
        # Connect to Gemini Live
        async with gemini.aio.live.connect(
            model=MODEL,
            config=CONFIG
        ) as session:

            # 1. Browser microphone -> Gemini
            async def browser_to_gemini():

                while True:
                    pcm = await ws.receive_bytes()

                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=pcm,
                            mime_type="audio/pcm;rate=16000"
                        )
                    )

            # 2. Gemini -> Browser speaker
            async def gemini_to_browser():

                while True:

                    async for response in session.receive():

                        if response.tool_call:
                            await answer_tool_call(
                                session,
                                response.tool_call
                            )

                        content = response.server_content

                        if not content:
                            continue

                        # Stop previous audio if interrupted
                        if content.interrupted:
                            await ws.send_text(
                                json.dumps({"type": "interrupted"})
                            )

                        # Send Gemini audio to browser
                        if content.model_turn:

                            for part in content.model_turn.parts:

                                if part.inline_data:
                                    await ws.send_bytes(
                                        part.inline_data.data
                                    )

                        # Send captions
                        text = (
                            content.output_transcription.text
                            if content.output_transcription
                            else None
                        )

                        if text:
                            await ws.send_text(
                                json.dumps({
                                    "type": "caption",
                                    "text": text
                                })
                            )

                        # Tell browser when response is complete
                        if content.turn_complete:
                            await ws.send_text(
                                json.dumps({"type": "done"})
                            )

            # 3. Run both tasks inside the Gemini session
            tasks = [
                asyncio.create_task(browser_to_gemini()),
                asyncio.create_task(gemini_to_browser())
            ]

            try:
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    if not task.cancelled() and task.exception():
                        raise task.exception()

            finally:
                # Stop both tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()

                await asyncio.gather(
                    *tasks,
                    return_exceptions=True
                )

    except WebSocketDisconnect:
        print("Browser disconnected from voice.")

    except Exception as e:
        print("Voice connection error:", str(e))

        try:
            await ws.send_text(
                json.dumps({
                    "type": "error",
                    "message": str(e)
                })
            )
            await ws.close(code=1011)

        except Exception:
            pass
