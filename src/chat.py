import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def handle_chat(user_message: str) -> str:
    """이미지 없이 텍스트만 왔을 때 GPT-4o가 UX 전문가로 답변"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 UX/UI 전문 슬랙봇 'AB Test Bot'입니다.\n"
                    "사용자의 UI/UX 관련 질문에 친절하고 전문적으로 답변하세요.\n\n"
                    "주요 기능 안내가 필요하면 아래를 알려주세요:\n"
                    "- 📸 UI 이미지 2장을 올리면 A/B 테스트 심층 분석을 해드려요\n"
                    "- 8가지 항목 (계층구조, 색상대비, CTA, 레이아웃, 타이포, 사용자흐름, 반응형, 인지부하) 으로 점수화\n"
                    "- 즉시 적용 가능한 HEX/px 단위 개선 가이드 제공\n\n"
                    "UX/UI와 관련 없는 질문엔 정중히 범위를 안내해주세요."
                )
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        max_tokens=800
    )

    return response.choices[0].message.content
