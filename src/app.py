import os
import sys
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

sys.path.insert(0, os.path.dirname(__file__))
from analyzer import analyze_ab_test
from chat import handle_chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = App(token=os.environ["SLACK_BOT_TOKEN"])
pending_images = {}


@app.event("message")
def handle_message(body, say, logger):
    event = body.get("event", {})
    subtype = event.get("subtype")
    user = event.get("user", "unknown")
    channel = event.get("channel", "unknown")
    session_key = f"{channel}_{user}"

    # ── 봇 자신의 메시지는 무시 ──
    if event.get("bot_id"):
        return

    # ── 파일 업로드 처리 ──
    if subtype == "file_share":
        files = event.get("files", [])
        if not files:
            return

        if session_key not in pending_images:
            pending_images[session_key] = []

        for file in files:
            if file.get("mimetype", "").startswith("image/"):
                pending_images[session_key].append(file)
                logger.info(f"이미지 추가: {file.get('name')}")

        image_count = len(pending_images[session_key])

        if image_count == 1:
            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ *첫 번째 이미지를 받았어요!*\n비교할 두 번째 UI 이미지도 올려주세요 🖼️"
                }
            }])

        elif image_count >= 2:
            img_a = pending_images[session_key][0]
            img_b = pending_images[session_key][1]
            pending_images[session_key] = []

            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔍 *두 이미지를 심층 분석 중이에요...*\nGPT-4o Vision이 8가지 항목으로 A/B 테스트를 진행하고 있어요. 잠시만 기다려주세요! ⏳"
                }
            }])

            try:
                slack_headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                result = analyze_ab_test(img_a, img_b, slack_headers)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])
                logger.info("✅ A/B 테스트 완료!")

            except Exception as e:
                logger.error(f"오류 발생: {e}", exc_info=True)
                say(f"❌ 분석 중 오류가 발생했어요: `{str(e)}`\n다시 시도해주세요!")
        return

    # ── 일반 텍스트 대화 처리 ──
    if subtype is None:
        text = event.get("text", "").strip()
        if not text:
            return

        logger.info(f"일반 대화 수신: {text[:50]}")
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
