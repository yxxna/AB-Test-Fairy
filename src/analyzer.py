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

    logger.info("GPT-4o Vision으로 분석 요청 중...")

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
    logger.info("분석 완료. 개선 프롬프트 생성 중...")

    prompt_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": (
                f"다음 A/B 테스트 분석 결과를 바탕으로, 두 디자인의 장점을 결합한 "
                "최적의 UI를 DALL-E 3로 생성하기 위한 영어 프롬프트를 작성해주세요.\n"
                "색상, 레이아웃, 버튼 스타일, 타이포그래피 등 구체적으로 작성하세요.\n"
                "프롬프트 텍스트만 출력하세요 (설명 없이).\n\n"
                f"분석 결과:\n{analysis_text}"
            )
        }],
        max_tokens=400
    )

    improvement_prompt = prompt_response.choices[0].message.content

    formatted_message = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔬 *A/B 테스트 분석 결과*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{analysis_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "_분석 완료! 이제 개선안 이미지를 생성할게요 🎨_"
    )

    return {
        "message": formatted_message,
        "improvement_prompt": improvement_prompt,
        "raw_analysis": analysis_text
    }
