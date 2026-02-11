# src/agent/nodes/document_analyzer.py

from src.core.observe import observe
from typing import Dict
import fitz
from docx import Document

from src.core.llm_factory import LLMFactory, langfuse_session


def _extract_pdf_via_gemini(file_path: str) -> str:
    """이미지 기반 PDF → Gemini Vision으로 텍스트 추출 (폴백)"""
    import base64
    from langchain_core.messages import HumanMessage

    llm, callbacks = LLMFactory.create(
        provider="google",
        model="gemini-2.0-flash",
        temperature=0.0,
    )

    with open(file_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    msg = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "이 PDF 문서의 모든 텍스트를 순서대로 추출해서 그대로 반환해주세요. 한국어와 영어 모두 포함하고, 표나 리스트 구조는 가능한 한 유지해주세요.",
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:application/pdf;base64,{pdf_b64}"},
            },
        ]
    )

    with langfuse_session(session_id="document_analyzer_vision"):
        resp = llm.invoke([msg], config={"callbacks": callbacks})

    if hasattr(resp, "content"):
        c = resp.content
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return "".join(
                b.get("text", str(b)) if isinstance(b, dict) else str(b)
                for b in c
            )
    return str(resp)


def extract_pdf_text(file_path: str) -> str:
    """PDF 파일에서 텍스트 추출. 일반 PDF는 PyMuPDF, 이미지 기반은 Gemini Vision 폴백."""
    doc = fitz.open(file_path)
    pages = list(doc)
    text_parts = [
        p.get_text("text", sort=True).strip()
        for p in pages
    ]
    total_chars = sum(len(t) for t in text_parts)
    doc.close()

    # 페이지당 평균 50자 미만이면 이미지 기반으로 판단 → Gemini Vision 사용
    if pages and total_chars < 50 * len(pages):
        return _extract_pdf_via_gemini(file_path)

    return "\n\n".join(p for p in text_parts if p)


def extract_word_text(file_path: str) -> str:
    """Word(DOCX) 파일에서 텍스트 추출"""
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


@observe(name="structure_document")
def structure_with_llm(text: str) -> Dict:
    """
    LLM(Gemini 3 Flash)으로 문서 내용 요약/구조화
    """
    # 1. Gemini 3 Flash 모델 생성
    llm, callbacks = LLMFactory.create(
        provider="google",
        model="gemini-2.0-flash",   # Gemini 2 Flash (API 사용 가능 모델)
        temperature=0.0,
    )

    # 텍스트 길이 제한
    truncated = text[:3000] if len(text) > 3000 else text

    prompt = f"""
    너는 문서 분석 에이전트야.
    아래 문서를 읽고 다음 정보를 한국어로 구조화해서 반환해.

    1. 한 문단 요약 (3~5문장)
    2. 주요 키워드 5~10개 (쉼표로 구분)
    3. 중요한 수치/날짜/고유명사 목록 (불릿 리스트)

    문서 내용:
    {truncated}
    """

    # 2. Langfuse 세션 안에서 호출
    with langfuse_session(session_id="document_analyzer"):
        response = llm.invoke(
            prompt,
            config={"callbacks": callbacks},
        )

    summary_text = response.content if hasattr(response, "content") else str(response)

    return {
        "text": text,
        "summary": summary_text,
        "metadata": {"length": len(text), "model": "gemini-2.0-flash"},
    }


@observe(name="document_analyzer")
def document_analyzer(state: Dict) -> Dict:
    """
    문서 파일을 분석해서 구조화된 데이터로 변환
    """
    state.setdefault("steps_log", [])
    state.setdefault("clean_data", None)

    file_path = state.get("file_path")
    if not file_path:
        state["steps_log"].append("[document_analyzer] ERROR: file_path missing")
        return state

    ext = file_path.split('.')[-1].lower()

    if ext == "pdf":
        text = extract_pdf_text(file_path)
    elif ext in ["docx", "doc"]:
        text = extract_word_text(file_path)
    else:
        state["steps_log"].append(f"[document_analyzer] Skipped: {ext} not supported")
        return state

    structured_data = structure_with_llm(text)

    state["clean_data"] = structured_data
    state["steps_log"].append(f"[document_analyzer] Processed {ext}: {len(text)} chars")

    return state
