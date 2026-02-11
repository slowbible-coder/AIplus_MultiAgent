# tests/test_document_analyzer.py

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# 환경 변수 로드 (.env는 프로젝트 루트에 있다고 가정)
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(project_root))

from src.agent.nodes.document_analyzer import (
    document_analyzer,
    extract_pdf_text,
    extract_word_text,
    structure_with_llm,
)


def test_pdf_extraction():
    """PDF 텍스트 + LLM 구조화 테스트"""
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  GOOGLE_API_KEY를 .env에 설정하세요 (Gemini 키)")
        return

    fixtures_dir = Path(__file__).parent / "fixtures"
    pdf_file = fixtures_dir / "20251211.pdf"

    if not pdf_file.exists():
        print(f"⚠️  테스트용 PDF가 없습니다: {pdf_file}")
        print(f"   {fixtures_dir} 폴더에 20251211.pdf 파일을 추가하세요")
        return

    state = {
        "file_path": str(pdf_file),
        "steps_log": [],
    }

    result = document_analyzer(state)

    assert "clean_data" in result
    assert result["clean_data"] is not None
    assert "text" in result["clean_data"]
    assert len(result["clean_data"]["text"]) > 0
    assert "summary" in result["clean_data"]
    print(f"✅ PDF 처리: {len(result['clean_data']['text'])} chars")
    print(f"📝 로그: {result['steps_log']}")


def test_docx_extraction():
    """Word 텍스트 추출 테스트"""
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  GOOGLE_API_KEY를 .env에 설정하세요")
        return

    fixtures_dir = Path(__file__).parent / "fixtures"
    # fixtures 폴더의 docx 파일 사용 (Ai1.docx, sample.docx 순으로 시도)
    docx_file = fixtures_dir / "Ai1.docx"
    if not docx_file.exists():
        docx_file = fixtures_dir / "sample.docx"
    if not docx_file.exists():
        print(f"⚠️  테스트용 DOCX가 없습니다: {fixtures_dir} (Ai1.docx 또는 sample.docx)")
        return

    state = {
        "file_path": str(docx_file),
        "steps_log": [],
    }

    result = document_analyzer(state)

    assert "clean_data" in result
    assert result["clean_data"]["text"]
    print(f"✅ Word 처리: {len(result['clean_data']['text'])} chars")


def test_unsupported_format():
    """지원하지 않는 형식 테스트 (API 키 불필요)"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    txt_file = fixtures_dir / "sample.txt"

    state = {
        "file_path": str(txt_file),
        "steps_log": [],
    }

    result = document_analyzer(state)
    assert len(result["steps_log"]) > 0
    assert "Skipped" in result["steps_log"][-1]
    print("✅ 지원하지 않는 형식 처리 확인")


if __name__ == "__main__":
    # Windows cp949 콘솔 인코딩 대응
    import io
    if sys.stdout.encoding and "utf" not in sys.stdout.encoding.lower():
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("[TEST] Document Analyzer 테스트 시작\n")

    # 필수 라이브러리 확인
    try:
        import fitz  # PyMuPDF
        from docx import Document
    except ImportError:
        print("[FAIL] 필수 라이브러리가 없습니다:")
        print("   pip install pymupdf python-docx")
        sys.exit(1)

    # API 키 안내
    if not os.getenv("GOOGLE_API_KEY"):
        print("[WARN] GOOGLE_API_KEY가 설정되지 않았습니다")
        print("   .env 파일에 GOOGLE_API_KEY를 설정하세요 (Gemini)")
        print("   PDF/Docx 테스트는 건너뛰고, unsupported_format만 실행됩니다.\n")

    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    print("[INFO] 테스트 파일 경로:", fixtures_dir)
    print("   - PDF: 20251211.pdf")
    print("   - Word: Ai1.docx")
    print("   - 미지원 형식: sample.txt\n")

    test_pdf_extraction()
    test_docx_extraction()
    test_unsupported_format()

    print("\n[DONE] 모든 테스트 완료!")
