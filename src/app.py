import os
import sys
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

sys.path.insert(0, os.path.dirname(__file__))
from analyzer import analyze_single, analyze_ab_test, analyze_flow
from chat import handle_chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("message")
def handle_message(body, say, logger):
    event = body.get("event", {})
    subtype = event.get("subtype")

    # 봇 메시지 무시
    if event.get("bot_id"):
        return

    slack_headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}

    # ── 이미지 업로드 ──
    if subtype == "file_share":
        files = event.get("files", [])
        images = [f for f in files if f.get("mimetype", "").startswith("image/")]
        context = event.get("text", "").strip()
        count = len(images)

        if count == 0:
            return

        try:
            # 1장: 단일 화면 분석
            if count == 1:
                say(blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔍 *이미지를 분석 중이에요...* ⏳"
                    }
                }])
                result = analyze_single(images[0], slack_headers, context)
                say(text=result)

            # 2장: A/B 테스트
            elif count == 2:
                say(blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔍 *2장 감지 → A/B 테스트 분석 시작!* ⏳"
                    }
                }])
                result = analyze_ab_test(images[0], images[1], slack_headers, context)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])

            # 3장+: UX 플로우 분석
            else:
                say(blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📱 *{count}장 감지 → UX 플로우 분석 시작!* ⏳"
                    }
                }])
                result = analyze_flow(images, slack_headers, context)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])

        except Exception as e:
            logger.error(f"분석 오류: {e}", exc_info=True)
            say(f"❌ 분석 중 오류가 발생했어요: `{str(e)}`")
        return

    # ── 텍스트 대화 ──
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
