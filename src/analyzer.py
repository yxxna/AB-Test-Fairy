import os
import base64
import requests
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def download_image_as_base64(file_info: dict, headers: dict) -> str:
    url = file_info.get("url_private_download") or file_info.get("url_private")
    if not url:
        raise ValueError("이미지 URL을 찾을 수 없어요.")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return base64.b64encode(response.content).decode("utf-8")


def analyze_ab_test(img_a_info: dict, img_b_info: dict, headers: dict) -> dict:
    img_a_b64 = download_image_as_base64(img_a_info, headers)
    img_b_b64 = download_image_as_base64(img_b_info, headers)
    img_a_mime = img_a_info.get("mimetype", "image/png")
    img_b_mime = img_b_info.get("mimetype", "image/png")

    logger.info("GPT-4o Vision 심층 분석 시작...")

    # 1차: 8항목 심층 A/B 분석
    analysis_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 10년 경력의 UX/UI 전문가입니다.\n"
                    "두 UI 디자인을 아래 8가지 항목으로 심층 분석하고 슬랙 마크다운으로 작성하세요.\n\n"
                    "각 항목마다 반드시:\n"
                    "- Image A 점수 (10점 만점)\n"
                    "- Image B 점수 (10점 만점)\n"
                    "- 각각의 근거 1~2줄\n"
                    "를 포함하세요.\n\n"
                    "【분석 항목 8가지】\n"
                    "1. 👁 시각적 계층구조 (Visual Hierarchy) — 정보 우선순위가 시각적으로 잘 표현되는가\n"
                    "2. 🌈 색상 대비 & 접근성 (Color Contrast & Accessibility) — WCAG 기준 충족 여부, 색맹 사용자 고려\n"
                    "3. 🎯 CTA 명확성 (Call-to-Action Clarity) — 버튼/액션이 직관적으로 눈에 띄는가\n"
                    "4. 📐 레이아웃 & 여백 (Layout & Whitespace) — 요소 간 균형, 여백의 적절성\n"
                    "5. 🔤 타이포그래피 (Typography) — 폰트 크기 위계, 가독성, 줄 간격\n"
                    "6. 🧭 사용자 흐름 (User Flow) — 사용자가 다음 행동을 자연스럽게 유도받는가\n"
                    "7. 📱 반응형 & 터치 친화성 (Responsiveness & Touch) — 모바일 환경 대응, 터치 영역 크기\n"
                    "8. 💡 정보 밀도 & 인지 부하 (Information Density & Cognitive Load) — 한 화면에 너무 많은 정보가 없는가\n\n"
                    "마지막에:\n"
                    "- 항목별 점수 합계 비교\n"
                    "- 🏆 최종 승자 선정 및 이유 2~3줄"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "아래 두 UI를 심층 분석해주세요. 첫 번째가 *Image A*, 두 번째가 *Image B*입니다."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{img_a_mime};base64,{img_a_b64}", "detail": "high"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{img_b_mime};base64,{img_b_b64}", "detail": "high"}
                    }
                ]
            }
        ],
        max_tokens=3000
    )

    analysis_text = analysis_response.choices[0].message.content
    logger.info("분석 완료. 개선 가이드 생성 중...")

    # 2차: 실전 디자인 개선 가이드
    guide_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": (
                    "위 A/B 분석 결과를 바탕으로 "
                    "디자이너/개발자가 *즉시 적용 가능한* 개선 가이드를 슬랙 마크다운으로 작성해주세요.\n\n"
                    "아래 5가지를 반드시 포함하세요:\n"
                    "1. 🎨 색상 토큰 개선 — 현재 문제 색상 → 권장 HEX 코드\n"
                    "2. 📐 간격/여백 — 현재 문제 → 권장 px/rem 값\n"
                    "3. 🔤 타이포그래피 — 폰트 크기, weight, line-height 권장값\n"
                    "4. 🔘 CTA 버튼 — 크기, 색상, 텍스트, radius 권장값\n"
                    "5. ⚡ 우선순위 액션 아이템 — 즉시/단기/장기로 구분해서 3~5개씩\n\n"
                    f"분석 결과:\n{analysis_text}"
                )
            }
        ],
        max_tokens=1500
    )

    design_guide = guide_response.choices[0].message.content

    analysis_message = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔬 *A/B 테스트 심층 분석 결과 (8항목)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{analysis_text}"
    )

    guide_message = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *즉시 적용 가능한 디자인 개선 가이드*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{design_guide}"
    )

    return {
        "analysis_message": analysis_message,
        "guide_message": guide_message,
    }
