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
    logger.info(f"이미지 다운로드 중: {file_info.get('name')}")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return base64.b64encode(response.content).decode("utf-8")


def analyze_ab_test(img_a_info: dict, img_b_info: dict, headers: dict) -> dict:
    img_a_b64 = download_image_as_base64(img_a_info, headers)
    img_b_b64 = download_image_as_base64(img_b_info, headers)
    img_a_mime = img_a_info.get("mimetype", "image/png")
    img_b_mime = img_b_info.get("mimetype", "image/png")

    logger.info("GPT-4o Vision으로 A/B 분석 요청 중...")

    # 1차: A/B 비교 분석
    analysis_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 10년 경력의 UX/UI 전문가입니다. "
                    "두 개의 UI 디자인을 A/B 테스트 관점에서 분석하고 슬랙 마크다운 형식으로 답변하세요.\n\n"
                    "분석 기준:\n"
                    "1. 시각적 계층구조 (Visual Hierarchy)\n"
                    "2. 색상 대비 및 가독성 (Color Contrast & Readability)\n"
                    "3. CTA(Call-to-Action) 명확성\n"
                    "4. 레이아웃 균형 (Layout Balance)\n"
                    "5. 사용자 흐름 (User Flow)\n\n"
                    "답변 형식:\n"
                    "- 각 항목을 이모지와 함께 명확하게 구분\n"
                    "- 최종 승자(A 또는 B)를 명확히 선정\n"
                    "- 개선이 필요한 구체적인 포인트 3~5가지 제시"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "아래 두 UI 이미지를 A/B 테스트 관점에서 비교 분석해주세요. 첫 번째가 *Image A*, 두 번째가 *Image B* 입니다."
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
        max_tokens=2000
    )

    analysis_text = analysis_response.choices[0].message.content
    logger.info("A/B 분석 완료. 디자인 개선 가이드 생성 중...")

    # 2차: 구체적인 디자인 개선 가이드
    guide_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": (
                    "다음 A/B 테스트 분석 결과를 바탕으로, "
                    "실제 디자이너/개발자가 바로 적용할 수 있는 구체적인 개선 가이드를 작성해주세요.\n\n"
                    "다음 항목을 포함해서 슬랙 마크다운으로 작성하세요:\n"
                    "1. 🎨 색상 개선 (구체적인 HEX 코드 포함)\n"
                    "2. 📐 간격/여백 개선 (px 단위로 구체적으로)\n"
                    "3. 🔤 타이포그래피 개선 (폰트 크기, 굵기)\n"
                    "4. 🔘 버튼/CTA 개선 (크기, 색상, 텍스트)\n"
                    "5. ⚡ 우선순위 적용 순서 (1순위~3순위)\n\n"
                    f"분석 결과:\n{analysis_text}"
                )
            }
        ],
        max_tokens=1000
    )

    design_guide = guide_response.choices[0].message.content

    # 슬랙 메시지 구성
    analysis_message = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔬 *A/B 테스트 분석 결과*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{analysis_text}"
    )

    guide_message = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *구체적인 디자인 개선 가이드*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{design_guide}"
    )

    return {
        "analysis_message": analysis_message,
        "guide_message": guide_message,
    }
