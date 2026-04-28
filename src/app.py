import os
import sys
import logging
from typing import Dict, Any, List, Optional

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


# ----------------------------
# 기본 유틸
# ----------------------------
def should_ignore_event(event: Dict[str, Any]) -> bool:
    subtype = event.get("subtype")

    if event.get("bot_id"):
        return True

    if subtype in {"message_changed", "message_deleted", "bot_message"}:
        return True

    return False


def extract_context(event: Dict[str, Any]) -> Dict[str, Any]:
    files = event.get("files", []) or []
    images = [f for f in files if (f.get("mimetype") or "").startswith("image/")]

    return {
        "user_id": event.get("user"),
        "channel_id": event.get("channel"),
        "thread_ts": event.get("thread_ts") or event.get("ts"),
        "text": (event.get("text") or "").strip(),
        "subtype": event.get("subtype"),
        "files": files,
        "images": images,
        "image_count": len(images),
    }


def build_slack_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}


def post_reply(say, text: Optional[str] = None, blocks: Optional[List[Dict[str, Any]]] = None, thread_ts: Optional[str] = None):
    payload = {}
    if text is not None:
        payload["text"] = text
    if blocks is not None:
        payload["blocks"] = blocks
    if thread_ts is not None:
        payload["thread_ts"] = thread_ts
    say(**payload)


def build_loading_block(message: str) -> List[Dict[str, Any]]:
    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": message
        }
    }]


# ----------------------------
# 분석요정용 프롬프트 보강
# ----------------------------
def build_ui_consulting_prompt(user_text: str) -> str:
    return f"""
너는 '분석요정'이라는 이름의 UI/UX 자문 전문 AI다.

역할:
- 화면 구조, 정보 우선순위, CTA, 가독성, 시각적 위계, 전환율 관점에서 조언한다.
- 사용자가 이미지를 주지 않아도 텍스트만으로 UI 자문을 수행한다.
- 추상적인 말보다 실무적으로 바로 적용 가능한 제안을 우선한다.

답변 형식:
1. 한줄 진단
2. 핵심 문제 3개
3. 개선안 3개
4. 우선순위
5. 바로 적용 가능한 예시 문구/레이아웃 제안

사용자 요청:
{user_text}
""".strip()


# ----------------------------
# 이미지 처리
# ----------------------------
def handle_image_message(say, context: Dict[str, Any]):
    images = context["images"]
    count = context["image_count"]
    user_text = context["text"]
    thread_ts = context["thread_ts"]

    slack_headers = build_slack_headers()

    try:
        if count == 1:
            post_reply(
                say,
                blocks=build_loading_block("🔍 *단일 화면 UI 분석을 시작할게요...* ⏳"),
                thread_ts=thread_ts
            )
            result = analyze_single(images[0], slack_headers, user_text)
            post_reply(say, text=result, thread_ts=thread_ts)

        elif count == 2:
            post_reply(
                say,
                blocks=build_loading_block("🧪 *2장 감지 → A/B 테스트 관점으로 분석할게요...* ⏳"),
                thread_ts=thread_ts
            )
            result = analyze_ab_test(images[0], images[1], slack_headers, user_text)
            post_reply(say, text=result["analysis_message"], thread_ts=thread_ts)
            post_reply(say, text=result["guide_message"], thread_ts=thread_ts)

        else:
            post_reply(
                say,
                blocks=build_loading_block(f"📱 *{count}장 감지 → UX 플로우 분석을 시작할게요...* ⏳"),
                thread_ts=thread_ts
            )
            result = analyze_flow(images, slack_headers, user_text)
            post_reply(say, text=result["analysis_message"], thread_ts=thread_ts)
            post_reply(say, text=result["guide_message"], thread_ts=thread_ts)

    except Exception as e:
        logger.error(f"이미지 분석 오류: {e}", exc_info=True)
        post_reply(say, text=f"❌ 이미지 분석 중 오류가 발생했어요: `{str(e)}`", thread_ts=thread_ts)


# ----------------------------
# 텍스트 처리
# ----------------------------
def handle_text_message(say, context: Dict[str, Any]):
    text = context["text"]
    thread_ts = context["thread_ts"]
    user_id = context["user_id"]
    channel_id = context["channel_id"]

    if not text:
        return

    try:
        prompt = build_ui_consulting_prompt(text)

        # 1차 호환용:
        # 기존 handle_chat(text) 시그니처 유지
        # 나중에 아래처럼 확장 추천:
        # handle_chat(text=prompt, user_id=user_id, channel_id=channel_id, thread_ts=thread_ts)
        reply = handle_chat(prompt)

        post_reply(say, text=reply, thread_ts=thread_ts)

    except Exception as e:
        logger.error(f"텍스트 대화 오류: {e}", exc_info=True)
        post_reply(say, text=f"❌ 대화 중 오류가 발생했어요: `{str(e)}`", thread_ts=thread_ts)


# ----------------------------
# 메인 이벤트 라우터
# ----------------------------
@app.event("message")
def handle_message(body, say, logger):
    event = body.get("event", {})

    if should_ignore_event(event):
        return

    context = extract_context(event)

    # 이미지가 하나라도 있으면 이미지 분석 우선
    if context["image_count"] > 0:
        handle_image_message(say, context)
        return

    # 이미지가 없고 텍스트가 있으면 UI 자문형 대화
    if context["text"]:
        handle_text_message(say, context)
        return


if __name__ == "__main__":
    logger.info("⚡ 분석요정 Slack Bot 시작 중...")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
