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
pending_context = {}  # 이미지와 함께 온 텍스트 저장


@app.event("message")
def handle_message(body, say, logger):
    event = body.get("event", {})
    subtype = event.get("subtype")
    user = event.get("user", "unknown")
    channel = event.get("channel", "unknown")
    session_key = f"{channel}_{user}"

    # ── 봇 자신의 메시지 무시 ──
    if event.get("bot_id"):
        return

    # ── 파일 업로드 처리 ──
    if subtype == "file_share":
        files = event.get("files", [])
        if not files:
            return

        # 이미지와 함께 온 텍스트(컨텍스트) 저장
        context_text = event.get("text", "").strip()
        if context_text:
            pending_context[session_key] = context_text
            logger.info(f"컨텍스트 저장: {context_text[:50]}")

        if session_key not in pending_images:
            pending_images[session_key] = []

        for file in files:
            if file.get("mimetype", "").startswith("image/"):
                pending_images[session_key].append(file)
                logger.info(f"이미지 추가: {file.get('name')} (총 {len(pending_images[session_key])}장)")

        image_count = len(pending_images[session_key])

        # 이미지 1장 → 대기
        if image_count == 1:
            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "✅ *이미지 1장을 받았어요!*\n"
                        "• A/B 테스트: 비교할 이미지 1장 더 올려주세요 🖼️\n"
                        "• UX 플로우 분석: 전체 화면 흐름 이미지를 올려주세요 📱"
                    )
                }
            }])

        # 이미지 2장 → A/B 테스트
        elif image_count == 2:
            images = pending_images.pop(session_key)
            context = pending_context.pop(session_key, "")

            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔍 *2장 감지 → A/B 테스트 심층 분석 시작!*\nGPT-4o Vision이 8가지 항목으로 분석 중이에요 ⏳"
                }
            }])

            try:
                slack_headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                result = analyze_ab_test(images[0], images[1], slack_headers, context)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])
                logger.info("✅ A/B 테스트 완료!")
            except Exception as e:
                logger.error(f"오류: {e}", exc_info=True)
                say(f"❌ 분석 중 오류가 발생했어요: `{str(e)}`")

        # 이미지 3장 이상 → UX 플로우 분석
        elif image_count >= 3:
            images = pending_images.pop(session_key)
            context = pending_context.pop(session_key, "")

            say(blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📱 *{image_count}장 감지 → UX 플로우 전체 분석 시작!*\n화면 흐름 전체를 순서대로 분석할게요 ⏳"
                }
            }])

            try:
                slack_headers = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}
                result = analyze_flow(images, slack_headers, context)
                say(text=result["analysis_message"])
                say(text=result["guide_message"])
                logger.info(f"✅ UX 플로우 분석 완료! ({image_count}장)")
            except Exception as e:
                logger.error(f"오류: {e}", exc_info=True)
                say(f"❌ 분석 중 오류가 발생했어요: `{str(e)}`")
        return

    # ── 일반 텍스트 대화 ──
    if subtype is None:
        text = event.get("text", "").strip()
        if not text:
            return
        logger.info(f"일반 대화: {text[:50]}")
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
