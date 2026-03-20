import os
import sys
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

sys.path.insert(0, os.path.dirname(__file__))
from analyzer import analyze_ab_test, analyze_flow
from chat import handle_chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = App(token=os.environ["SLACK_BOT_TOKEN"])
pending_images = {}
pending_context = {}


@app.event("message")
def handle_message(body, say, logger):
    event = body.get("event", {})
    subtype = event.get("subtype")
    user = event.get("user", "unknown")
    channel = event.get("channel", "unknown")
    session_key = f"{channel}_{user}"

    if event.get("bot_id"):
        return

    if subtype == "file_share":
        files = event.get("files", [])
        if not files:
            return

        context_text = event.get("text", "").strip()
        if context_text:
            pending_context[session_key] = context_text

        if session_key not in pending_images:
            pending_images[session_key] = []

        for file in files:
            if file.get("mimetype", "").startswith("image/"):
                pending_images[session_key].append(file)

        image_count = len(pending_images[session_key])

        if image_count == 1:
            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "✅ *이미지 1장을 받았어요!*\n"
                        "• A/B 테스트: 비교할 이미지 1장 더 올려주세요\n"
                        "• UX 플로우 분석: 전체 화면 흐름 이미지를 올려주세요"
                    )
                }
            }])

        elif image_count == 2:
            images = pending_images.pop(session_key)
            context = pending_context.pop(session_key, "")
            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔍 *2장 감지 → A/B 테스트 분석 시작!*\nGPT-4o Vision이 8가지 항목으로 분석 중이에요 ⏳"
                }
            }])
            try:
                slack_headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                result = analyze_ab_test(images[0], images[1], slack_headers, context)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])
            except Exception as e:
                logger.error(f"오류: {e}", exc_info=True)
                say(f"❌ 오류가 발생했어요: `{str(e)}`")

        elif image_count >= 3:
            images = pending_images.pop(session_key)
            context = pending_context.pop(session_key, "")
            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📱 *{image_count}장 감지 → UX 플로우 전체 분석 시작!* ⏳"
                }
            }])
            try:
                slack_headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                result = analyze_flow(images, slack_headers, context)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])
            except Exception as e:
                logger.error(f"오류: {e}", exc_info=True)
                say(f"❌ 오류가 발생했어요: `{str(e)}`")
        return

    if subtype is None:
        text = event.get("text", "").strip()
        if not text:
            return
        try:
            reply = handle_chat(text)
            say(text=reply)
        except Exception as e:
            logger.error(f"대화 오류: {e}", exc_info=True)
            say(f"❌ 오류가 발생했어요: `{str(e)}`")


if __name__ == "__main__":
    logger.info("⚡ Slack A/B Test Bot 시작 중...")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
