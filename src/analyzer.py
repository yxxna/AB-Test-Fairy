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


# ───────────────────────────────────────────
# A/B 테스트 (2장)
# ───────────────────────────────────────────
def analyze_ab_test(img_a_info: dict, img_b_info: dict, headers: dict, context: str = "") -> dict:
    img_a_b64 = download_image_as_base64(img_a_info, headers)
    img_b_b64 = download_image_as_base64(img_b_info, headers)
    img_a_mime = img_a_info.get("mimetype", "image/png")
    img_b_mime = img_b_info.get("mimetype", "image/png")

    context_prompt = f"\n\n📌 추가 컨텍스트:\n{context}" if context else ""

    analysis_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 10년 경력의 UX/UI 전문가입니다.\n"
                    "두 UI 디자인을 아래 8가지 항목으로 심층 분석하고 슬랙 마크다운으로 작성하세요.\n"
                    "각 항목마다 Image A/B 점수(10점 만점)와 근거를 포함하세요.\n\n"
                    "【분석 8항목】\n"
                    "1. 👁 시각적 계층구조\n"
                    "2. 🌈 색상 대비 & 접근성 (WCAG 기준)\n"
                    "3. 🎯 CTA 명확성\n"
                    "4. 📐 레이아웃 & 여백\n"
                    "5. 🔤 타이포그래피\n"
                    "6. 🧭 사용자 흐름\n"
                    "7. 📱 반응형 & 터치 친화성\n"
                    "8. 💡 인지 부하\n\n"
                    "마지막에 점수 합계 비교 + 🏆 최종 승자 선정"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"아래 두 UI를 분석해주세요. 첫 번째가 Image A, 두 번째가 Image B입니다.{context_prompt}"
                    },
                    {"type": "image_url", "image_url": {"url": f"data:{img_a_mime};base64,{img_a_b64}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:{img_b_mime};base64,{img_b_b64}", "detail": "high"}}
                ]
            }
        ],
        max_tokens=3000
    )

    analysis_text = analysis_response.choices[0].message.content

    guide_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": (
                "위 분석 결과를 바탕으로 즉시 적용 가능한 개선 가이드를 작성해주세요.\n"
                "1. 🎨 색상 토큰 (현재→권장 HEX)\n"
                "2. 📐 간격/여백 (권장 px/rem)\n"
                "3. 🔤 타이포그래피 (크기, weight, line-height)\n"
                "4. 🔘 CTA 버튼 (크기, 색상, radius)\n"
                "5. ⚡ 우선순위 액션 (즉시/단기/장기)\n\n"
                f"분석:\n{analysis_text}"
            )
        }],
        max_tokens=1500
    )

    return {
        "analysis_message": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔬 *A/B 테스트 심층 분석 (8항목)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{analysis_text}"
        ),
        "guide_message": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *즉시 적용 가능한 개선 가이드*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{guide_response.choices[0].message.content}"
        )
    }


# ───────────────────────────────────────────
# UX 플로우 분석 (3장 이상)
# ───────────────────────────────────────────
def analyze_flow(images: list, headers: dict, context: str = "") -> dict:
    image_contents = []
    for i, img_info in enumerate(images):
        b64 = download_image_as_base64(img_info, headers)
        mime = img_info.get("mimetype", "image/png")
        image_contents.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}
        })

    context_prompt = f"\n\n📌 요청자 컨텍스트:\n{context}" if context else ""
    count = len(images)

    # 1차: 플로우 분석
    flow_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 10년 경력의 UX/UI 전문가입니다.\n"
                    "제공된 화면들을 순서대로 분석하여 전체 UX 플로우를 평가하세요.\n\n"
                    "【분석 항목】\n"
                    "1. 🗺 전체 플로우 요약 — 각 화면의 역할을 1줄씩\n"
                    "2. 😓 사용자 피로도 — 단계 수, 인<span class="cursor">█</span>

cat > src/analyzer.py << 'EOF'
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


# ───────────────────────────────────────────
# A/B 테스트 (2장)
# ───────────────────────────────────────────
def analyze_ab_test(img_a_info: dict, img_b_info: dict, headers: dict, context: str = "") -> dict:
    img_a_b64 = download_image_as_base64(img_a_info, headers)
    img_b_b64 = download_image_as_base64(img_b_info, headers)
    img_a_mime = img_a_info.get("mimetype", "image/png")
    img_b_mime = img_b_info.get("mimetype", "image/png")

    context_prompt = f"\n\n📌 추가 컨텍스트:\n{context}" if context else ""

    analysis_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 10년 경력의 UX/UI 전문가입니다.\n"
                    "두 UI 디자인을 아래 8가지 항목으로 심층 분석하고 슬랙 마크다운으로 작성하세요.\n"
                    "각 항목마다 Image A/B 점수(10점 만점)와 근거를 포함하세요.\n\n"
                    "【분석 8항목】\n"
                    "1. 👁 시각적 계층구조\n"
                    "2. 🌈 색상 대비 & 접근성 (WCAG 기준)\n"
                    "3. 🎯 CTA 명확성\n"
                    "4. 📐 레이아웃 & 여백\n"
                    "5. 🔤 타이포그래피\n"
                    "6. 🧭 사용자 흐름\n"
                    "7. 📱 반응형 & 터치 친화성\n"
                    "8. 💡 인지 부하\n\n"
                    "마지막에 점수 합계 비교 + 🏆 최종 승자 선정"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"아래 두 UI를 분석해주세요. 첫 번째가 Image A, 두 번째가 Image B입니다.{context_prompt}"
                    },
                    {"type": "image_url", "image_url": {"url": f"data:{img_a_mime};base64,{img_a_b64}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:{img_b_mime};base64,{img_b_b64}", "detail": "high"}}
                ]
            }
        ],
        max_tokens=3000
    )

    analysis_text = analysis_response.choices[0].message.content

    guide_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": (
                "위 분석 결과를 바탕으로 즉시 적용 가능한 개선 가이드를 작성해주세요.\n"
                "1. 🎨 색상 토큰 (현재→권장 HEX)\n"
                "2. 📐 간격/여백 (권장 px/rem)\n"
                "3. 🔤 타이포그래피 (크기, weight, line-height)\n"
                "4. 🔘 CTA 버튼 (크기, 색상, radius)\n"
                "5. ⚡ 우선순위 액션 (즉시/단기/장기)\n\n"
                f"분석:\n{analysis_text}"
            )
        }],
        max_tokens=1500
    )

    return {
        "analysis_message": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔬 *A/B 테스트 심층 분석 (8항목)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{analysis_text}"
        ),
        "guide_message": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *즉시 적용 가능한 개선 가이드*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{guide_response.choices[0].message.content}"
        )
    }


# ───────────────────────────────────────────
# UX 플로우 분석 (3장 이상)
# ───────────────────────────────────────────
def analyze_flow(images: list, headers: dict, context: str = "") -> dict:
    image_contents = []
    for i, img_info in enumerate(images):
        b64 = download_image_as_base64(img_info, headers)
        mime = img_info.get("mimetype", "image/png")
        image_contents.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}
        })

    context_prompt = f"\n\n📌 요청자 컨텍스트:\n{context}" if context else ""
    count = len(images)

    # 1차: 플로우 분석
    flow_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 10년 경력의 UX/UI 전문가입니다.\n"
                    "제공된 화면들을 순서대로 분석하여 전체 UX 플로우를 평가하세요.\n\n"
                    "【분석 항목】\n"
                    "1. 🗺 전체 플로우 요약 — 각 화면의 역할을 1줄씩\n"
                    "2. 😓 사용자 피로도 — 단계 수, 인지 부하, 이탈 위험 구간\n"
                    "3. 😊 만족감 & 감정 곡선 — 각 단계에서 예상되는 감정 변화\n"
                    "4. 🎯 전환율 예측 — 각 단계별 이탈 가능성 (높음/중간/낮음)\n"
                    "5. ♿ 접근성 & 대상 사용자 적합성 — 타겟 유저 기준 평가\n"
                    "6. 🚨 가장 큰 문제 구간 — 즉시 개선이 필요한 화면 지목\n"
                    "7. ✅ 잘 된 점 — 유지해야 할 UX 요소\n\n"
                    "점수: 전체 플로우 UX 점수 (100점 만점)"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"아래 {count}장의 화면을 순서대로 분석해주세요. 화면 1번부터 {count}번까지입니다.{context_prompt}"
                    },
                    *image_contents
                ]
            }
        ],
        max_tokens=3000
    )

    flow_text = flow_response.choices[0].message.content

    # 2차: 개선 가이드
    guide_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": (
                "위 UX 플로우 분석을 바탕으로 구체적인 개선 가이드를 작성해주세요.\n\n"
                "1. ✂️ 제거/통합 가능한 단계 — 줄일 수 있는 화면\n"
                "2. 🔧 화면별 즉시 개선사항 — 각 화면 번호 기준으로\n"
                "3. 💬 UX 카피 개선 — 더 명확한 문구 제안\n"
                "4. 📊 예상 개선 효과 — 전환율/만족도 변화 예측\n"
                "5. ⚡ 우선순위 액션 (즉시/단기/장기)\n\n"
                f"분석:\n{flow_text}"
            )
        }],
        max_tokens=1500
    )

    return {
        "analysis_message": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 *UX 플로우 분석 결과 ({count}장)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{flow_text}"
        ),
        "guide_message": (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔧 *플로우 개선 가이드*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{guide_response.choices[0].message.content}"
        )
    }
