"""
Document Analyzer 웹앱 - test_document_analyzer.py 기반
PDF/DOCX 업로드 → Gemini API로 문서 구조화·요약

실행: streamlit run webapp/document_analyzer_app.py
"""

# === STEP 1: .env 로드 (다른 import보다 먼저!) ===
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / ".env")

# === STEP 2: import ===
import streamlit as st
import os
import tempfile
from typing import Tuple, Optional

# === 페이지 설정 ===
st.set_page_config(
    page_title="문서 분석 (Gemini)",
    page_icon="📄",
    layout="wide",
)


def check_gemini_ready() -> Tuple[bool, str]:
    """
    Gemini API 적용 여부 확인
    Returns: (준비됨, 메시지)
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return False, "⚠️ GOOGLE_API_KEY가 .env에 설정되지 않았습니다. (Gemini API 키 필요)"

    # Gemini LLM 연결 확인
    from src.core.llm_factory import LLMFactory

    try:
        llm, _ = LLMFactory.create(
            provider="google",
            model="gemini-2.0-flash",  # document_analyzer와 동일
            temperature=0.0,
        )
        # 연결 테스트 (실제 호출 없이 객체만 생성)
        return True, f"✅ Gemini API 준비 완료 (GOOGLE_API_KEY: {api_key[:8]}...)"
    except Exception as e:
        return False, f"❌ Gemini API 연결 실패: {e}"


def run_document_analysis(file_path: str) -> Optional[dict]:
    """document_analyzer 실행 (test_document_analyzer와 동일)"""
    from src.agent.nodes.document_analyzer import document_analyzer

    state = {
        "file_path": file_path,
        "steps_log": [],
    }
    return document_analyzer(state)


def main():
    st.title("📄 문서 분석 (Gemini API)")

    # Gemini API 상태 확인
    ready, msg = check_gemini_ready()
    if not ready:
        st.error(msg)
        st.info("💡 .env 파일에 `GOOGLE_API_KEY=your-key` 를 추가한 뒤 앱을 재시작하세요.")
        st.code("GOOGLE_API_KEY=AIza...", language="bash")
        return

    st.success(msg)
    st.divider()

    st.markdown("**PDF 또는 Word(DOCX) 파일**을 업로드하면 Gemini가 요약·구조화합니다.")

    uploaded_file = st.file_uploader(
        "파일 업로드",
        type=["pdf", "docx", "doc"],
        help="PDF 또는 DOCX 파일을 선택하세요",
    )

    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext not in ["pdf", "docx", "doc"]:
            st.warning("지원 형식: PDF, DOCX, DOC")
            return

        # 임시 파일로 저장
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.caption(f"📁 {uploaded_file.name} ({uploaded_file.size:,} bytes)")

        if st.button("🚀 분석 시작", type="primary"):
            with st.spinner("Gemini가 문서를 분석하고 있습니다..."):
                result = run_document_analysis(temp_path)

            if result and "clean_data" in result and result["clean_data"]:
                clean = result["clean_data"]
                st.success("분석 완료!")

                st.markdown("### 📝 AI 요약")
                with st.container(border=True):
                    st.markdown(clean.get("summary", "-"))

                st.markdown("### 📊 메타데이터")
                st.json(clean.get("metadata", {}))

                st.markdown("### 📜 원문 (일부)")
                text = clean.get("text", "")
                preview = text[:2000] + "..." if len(text) > 2000 else text
                st.text_area("원문", preview, height=150, disabled=True)

                if "steps_log" in result:
                    st.caption(f"로그: {result['steps_log']}")
            else:
                st.warning("분석 결과가 없습니다. 형식을 확인해주세요.")
                if "steps_log" in result:
                    st.info(result["steps_log"])


if __name__ == "__main__":
    main()
