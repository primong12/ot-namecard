#!/usr/bin/env python3
# OT 이름표 생성기 — 완전 자급자족(오프라인) 단일 HTML 빌드 스크립트
# 라이브러리/폰트/얼굴모델을 모두 HTML 한 파일에 내장합니다.
import base64, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL  = ROOT / "build" / "app.template.html"
OUT  = ROOT / "HSproduce_app.html"

def read_text(p): return (ROOT / p).read_text(encoding="utf-8")
def read_b64(p):  return base64.b64encode((ROOT / p).read_bytes()).decode("ascii")

def inline_script(p):
    # 미니파이된 JS 안의 </script> 가 HTML 파싱을 깨지 않도록 이스케이프
    js = read_text(p).replace("</script", "<\\/script")
    return f"<script>\n{js}\n</script>"

html = TPL.read_text(encoding="utf-8")

# 1) 얼굴 모델 가로채기 스크립트 — 반드시 face-api 보다 "먼저" 실행되어야 함.
#    (face-api/tfjs 는 로드 시점의 fetch 를 기억해두기 때문)
#    내장할 모델 파일들: 얼굴 검출 + 눈/코/입 위치(랜드마크, tiny)
MANIFESTS = [
    "tiny_face_detector_model-weights_manifest.json",
    "face_landmark_68_tiny_model-weights_manifest.json",
]
BINS = [
    "tiny_face_detector_model.bin",
    "face_landmark_68_tiny_model.bin",
]
entries = []
for name in MANIFESTS:
    data = json.dumps(json.loads(read_text(f"models/{name}")), ensure_ascii=False, separators=(",", ":"))
    entries.append(f'  "{name}": {{type:"json", data:{data}}}')
for name in BINS:
    entries.append(f'  "{name}": {{type:"bin", data:"{read_b64("models/" + name)}"}}')
model_files = "{\n" + ",\n".join(entries) + "\n}"
shim = (
    "<script>\n"
    "// ===== 오프라인 자원: 얼굴 인식 모델을 이 파일에 내장 =====\n"
    "// file:// 환경에서 브라우저가 외부 파일 읽기를 막으므로, 모델 요청을\n"
    "// 가로채 내장 데이터로 응답합니다. (인터넷/외부파일 불필요)\n"
    f"const MODEL_FILES = {model_files};\n"
    "(function(){\n"
    "  window.__shimHit = 0;\n"
    "  const real = window.fetch ? window.fetch.bind(window) : null;\n"
    "  function bytesFromB64(b64){ const bin=atob(b64); const u=new Uint8Array(bin.length);\n"
    "    for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i); return u; }\n"
    "  window.fetch = function(input, init){\n"
    "    const url = typeof input==='string' ? input : (input && input.url) || '';\n"
    "    for(const fn in MODEL_FILES){\n"
    "      if(url.indexOf(fn) >= 0){\n"
    "        window.__shimHit++; const f = MODEL_FILES[fn];\n"
    "        if(f.type==='json') return Promise.resolve(new Response(JSON.stringify(f.data),\n"
    "          {status:200, headers:{'Content-Type':'application/json'}}));\n"
    "        return Promise.resolve(new Response(bytesFromB64(f.data),\n"
    "          {status:200, headers:{'Content-Type':'application/octet-stream'}}));\n"
    "      }\n"
    "    }\n"
    "    return real ? real(input, init) : Promise.reject(new Error('fetch unavailable'));\n"
    "  };\n"
    "})();\n"
    "</script>"
)
html = html.replace("<!--SHIM_SCRIPT-->", shim)

# 2) 라이브러리 인라인
html = html.replace("<!--JSZIP_SCRIPT-->",   inline_script("vendor/jszip.min.js"))
html = html.replace("<!--FACEAPI_SCRIPT-->", inline_script("vendor/face-api.min.js"))

# 3) 폰트(Pretendard ExtraBold/Bold/SemiBold) data URL 내장
html = html.replace("__FONT_SRC__",      f"data:font/woff2;base64,{read_b64('fonts/Pretendard-ExtraBold.woff2')}")
html = html.replace("__FONT_BOLD__",     f"data:font/woff2;base64,{read_b64('fonts/Pretendard-Bold.woff2')}")
html = html.replace("__FONT_SEMIBOLD__", f"data:font/woff2;base64,{read_b64('fonts/Pretendard-SemiBold.woff2')}")

# 4) 이름표 띠 디자인 이미지 data URL 내장
html = html.replace("__TAG_SRC__", f"data:image/png;base64,{read_b64('assets/tag.png')}")

# 5) 엘리트클럽 로고(목걸이 명찰·스탠드 이름표용) data URL 내장
html = html.replace("__LOGO_SRC__", f"data:image/png;base64,{read_b64('assets/logo.png')}")

# 6) 필기체 폰트(Great Vibes · 목걸이 명찰 행사명) data URL 내장
html = html.replace("__FONT_SCRIPT__", f"data:font/woff2;base64,{read_b64('fonts/GreatVibes-Regular.woff2')}")

# 남은 토큰이 없는지 검증
for token in ("<!--SHIM_SCRIPT-->", "<!--JSZIP_SCRIPT-->", "<!--FACEAPI_SCRIPT-->", "__FONT_SRC__", "__FONT_BOLD__", "__FONT_SEMIBOLD__", "__TAG_SRC__", "__LOGO_SRC__", "__FONT_SCRIPT__"):
    if token in html:
        sys.exit(f"치환되지 않은 토큰이 남아 있습니다: {token}")

OUT.write_text(html, encoding="utf-8")
# GitHub Pages 기본 문서로도 동일 내용 출력 (온라인 링크용)
(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"빌드 완료 → {OUT}  ({len(html)/1024/1024:.2f} MB)  + index.html")
