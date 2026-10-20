"""재능넷 대표 이미지 14장 생성 (1000x750). 글자와 단순 도형만 사용한다.
실행: python3 make_images.py   (이 폴더의 fonts/NotoSansKR-VF.ttf 사용, OFL)
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "NotoSansKR-VF.ttf")
OUT = os.path.join(HERE, "이미지")
W, H = 1000, 750
_cache = {}


def F(size, w=500):
    k = (size, w)
    if k not in _cache:
        f = ImageFont.truetype(FONT, size)
        f.set_variation_by_axes([w])
        _cache[k] = f
    return _cache[k]


def tw(d, s, f):
    return d.textlength(s, font=f)


def wrap(d, s, f, maxw):
    lines = []
    for para in s.split("\n"):
        cur = ""
        for word in para.split(" "):
            t = (cur + " " + word).strip()
            if tw(d, t, f) <= maxw:
                cur = t
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for ch in word:
                if tw(d, cur + ch, f) <= maxw:
                    cur += ch
                else:
                    lines.append(cur)
                    cur = ch
        lines.append(cur)
    return lines


def text(d, xy, s, size, fill, w=500, maxw=None, gap=1.35, anchor="l"):
    f = F(size, w)
    x, y = xy
    lines = wrap(d, s, f, maxw) if maxw else s.split("\n")
    for ln in lines:
        lx = x
        if anchor == "m":
            lx = x - tw(d, ln, f) / 2
        d.text((lx, y), ln, font=f, fill=fill)
        right = lx + tw(d, ln, f)
        assert right <= W - 20 and y + size <= H - 10, (s[:12], right, y)
        y += int(size * gap)
    return y


def canvas(bg):
    im = Image.new("RGB", (W, H), bg)
    return im, ImageDraw.Draw(im)


def save(im, n):
    im.save(os.path.join(OUT, f"{n:02d}.png"))


# 01 단계형: 먼저 받는 것 -> 결정 -> 본문
def i01():
    im, d = canvas("#F4EFE6")
    text(d, (60, 50), "맡기기 전에\n먼저 읽어 보세요", 54, "#2B2B2B", 800)
    text(d, (60, 215), "목차 한 장과 첫 단락을 먼저 받고, 그 뒤에 본문을 정합니다.", 27, "#5A4A3A", 500, maxw=880)
    xs = [60, 370, 680]
    labels = [("1", "목차안 1장"), ("2", "첫 단락"), ("3", "마음에 들면 본문")]
    for x, (n, l) in zip(xs, labels):
        d.rectangle([x, 290, x + 260, 440], fill="#FFFFFF", outline="#2B2B2B", width=3)
        d.rectangle([x, 290, x + 260, 340], fill="#2B2B2B")
        text(d, (x + 18, 297), "단계 " + n, 28, "#F4EFE6", 700)
        text(d, (x + 18, 365), l, 32, "#2B2B2B", 700)
    for x in (322, 632):
        d.polygon([(x, 350), (x + 36, 365), (x, 380)], fill="#B5532B")
    text(d, (60, 500), "받는 것", 30, "#B5532B", 800)
    text(d, (60, 548), "보고서·제안서·소개서 본문 한글(HWP) 또는 워드 파일\n수정 2회, 질문 목록 회신 포함", 29, "#2B2B2B", 500)
    save(im, 1)


# 02 좌우 대조형
def i02():
    im, d = canvas("#EAF1F6")
    d.rectangle([0, 0, W, 130], fill="#1F3A52")
    text(d, (50, 32), "첫 문단 번역을 먼저 봅니다", 48, "#FFFFFF", 800)
    d.rectangle([50, 170, 480, 470], fill="#FFFFFF", outline="#1F3A52", width=3)
    d.rectangle([520, 170, 950, 470], fill="#FFFFFF", outline="#1F3A52", width=3)
    text(d, (70, 185), "원문", 26, "#1F3A52", 800)
    text(d, (540, 185), "번역", 26, "#1F3A52", 800)
    for i in range(7):
        y = 240 + i * 32
        d.rectangle([70, y, 70 + (360 if i < 6 else 220), y + 12], fill="#B9C7D3")
        d.rectangle([540, y, 540 + (360 if i < 6 else 160), y + 12], fill="#7FA3C0")
    text(d, (50, 510), "영어·중국어 번역, 원문과 번역문을 나란히 놓은 대조표 PDF", 29, "#1F3A52", 700, maxw=900)
    text(d, (50, 600), "번역문 DOCX 1부\n수정 2회, 오역과 누락은 횟수 밖", 29, "#2B2B2B", 500)
    save(im, 2)


# 03 세로 제목형
def i03():
    im, d = canvas("#F7F7F2")
    d.rectangle([0, 0, 260, H], fill="#233D2E")
    title = "직무수행계획서"
    y = 70
    for ch in title:
        d.text((95, y), ch, font=F(70, 800), fill="#F7F7F2")
        y += 88
    text(d, (310, 70), "임기제·경력경쟁\n공무원 전자책", 50, "#233D2E", 800)
    text(d, (310, 230), "직무수행계획서와 자기소개서를\n어떤 순서로 짜는지 정리했습니다.", 31, "#2B2B2B", 500)
    d.rectangle([310, 370, 940, 374], fill="#233D2E")
    text(d, (310, 400), "받는 것", 28, "#7A5A1E", 800)
    text(d, (310, 445), "PDF 전자책 1권, 목차 10장\n6개월·1년 계획 쓰는 순서\n제출 전 점검표", 30, "#2B2B2B", 500)
    text(d, (310, 640), "구매 전 목차와 3장 두 쪽 미리보기", 26, "#233D2E", 700)
    save(im, 3)


# 04 표형
def i04():
    im, d = canvas("#FFFFFF")
    text(d, (50, 40), "NCS 자기소개서\n문항 유형별 뼈대 30", 50, "#3B2A6B", 800)
    rows = [("의사소통", 4), ("문제해결", 5), ("자원관리", 4), ("조직이해", 4),
            ("대인관계", 5), ("직업윤리", 4), ("지원동기·직무", 4)]
    x0, y0 = 50, 220
    d.rectangle([x0, y0, 560, y0 + 44], fill="#3B2A6B")
    text(d, (x0 + 15, y0 + 5), "문항 유형", 25, "#FFFFFF", 700)
    text(d, (x0 + 360, y0 + 5), "뼈대", 25, "#FFFFFF", 700)
    for i, (n, c) in enumerate(rows):
        y = y0 + 44 + i * 44
        d.rectangle([x0, y, 560, y + 44], fill="#F1EEF8" if i % 2 == 0 else "#FFFFFF", outline="#C9C2DE")
        text(d, (x0 + 15, y + 5), n, 25, "#2B2B2B", 500)
        text(d, (x0 + 380, y + 5), str(c), 25, "#2B2B2B", 700)
    y = y0 + 44 + 7 * 44
    d.rectangle([x0, y, 560, y + 44], fill="#3B2A6B")
    text(d, (x0 + 15, y + 5), "합계", 25, "#FFFFFF", 700)
    text(d, (x0 + 380, y + 5), "30", 25, "#FFFFFF", 700)
    text(d, (610, 225), "받는 것", 28, "#3B2A6B", 800)
    text(d, (610, 275), "문항 유형 구별표\n첫 줄에 무엇을 쓸지 정한\n답안 뼈대 30개\n제출 전 점검표", 28, "#2B2B2B", 500)
    text(d, (610, 520), "PDF 전자책", 28, "#3B2A6B", 800)
    save(im, 4)


# 05 비율 막대형
def i05():
    im, d = canvas("#FBF3E8")
    text(d, (50, 40), "「상황·행동·결과」\n답안 틀 25", 54, "#7A2E1B", 800)
    text(d, (50, 200), "1000자 답안에서 칸마다 몇 자를 쓰는지 정해 둔 틀입니다.", 26, "#2B2B2B", 500, maxw=900)
    parts = [("상황", 150, "#D9A441"), ("행동", 550, "#7A2E1B"), ("결과", 200, "#4F7A5A"), ("연결", 100, "#6B6B6B")]
    x = 50
    for n, c, col in parts:
        wd = int(c / 1000 * 900)
        d.rectangle([x, 290, x + wd, 380], fill=col)
        text(d, (x + 10, 300), n, 26, "#FFFFFF", 700)
        text(d, (x + 10, 335), f"{c}자", 24, "#FFFFFF", 500)
        x += wd
    text(d, (50, 440), "문항 25개", 28, "#7A2E1B", 800)
    text(d, (50, 485), "지원동기 5, 직무 경험 6, 협업·갈등 5\n도전·실패 5, 성장·학습 4", 28, "#2B2B2B", 500)
    text(d, (50, 610), "받는 것  PDF 전자책 1권, 칸마다 쓰는 질문과 점검 질문", 27, "#2B2B2B", 700, maxw=900)
    save(im, 5)


# 06 전후 비교
def i06():
    im, d = canvas("#F2F2F2")
    text(d, (50, 35), "경력은 길어도\n이력서는 한 장", 52, "#1E1E1E", 800)
    text(d, (50, 195), "줄이기 전", 26, "#8A8A8A", 700)
    text(d, (560, 195), "줄인 뒤", 26, "#C23B22", 800)
    for k in range(3):
        x = 50 + k * 120
        d.rectangle([x, 240, x + 100, 420], fill="#FFFFFF", outline="#8A8A8A", width=2)
        for j in range(8):
            d.rectangle([x + 10, 255 + j * 20, x + 90, 262 + j * 20], fill="#CFCFCF")
    d.polygon([(430, 310), (500, 310), (500, 285), (545, 330), (500, 375), (500, 350), (430, 350)], fill="#1E1E1E")
    d.rectangle([600, 240, 740, 420], fill="#FFFFFF", outline="#C23B22", width=4)
    d.rectangle([612, 252, 728, 272], fill="#C23B22")
    for j in range(7):
        d.rectangle([612, 288 + j * 18, 728, 296 + j * 18], fill="#E2B1A8")
    text(d, (780, 280), "1쪽", 54, "#C23B22", 800)
    text(d, (50, 470), "이력서 1장과 경력기술서 1장을 줄이는 순서", 30, "#1E1E1E", 800, maxw=900)
    text(d, (50, 530), "받는 것\nPDF 전자책 1권, 작업표와 한 장 레이아웃\n두 줄 요약 쓰는 법", 28, "#2B2B2B", 500)
    save(im, 6)


# 07 막대 그래프형
def i07():
    im, d = canvas("#EEF4EE")
    text(d, (50, 35), "면접 질문 100과\n답변 구조", 54, "#1D4B2B", 800)
    rows = [("자기소개·지원동기", 10), ("직무 역량", 20), ("경험·성과", 20), ("인성·태도", 15),
            ("조직 적응·갈등", 15), ("압박·돌발", 10), ("역질문", 10)]
    y = 215
    for n, c in rows:
        text(d, (50, y), n, 24, "#2B2B2B", 500)
        d.rectangle([290, y + 3, 290 + c * 24, y + 33], fill="#1D4B2B")
        text(d, (290 + c * 24 + 12, y), str(c), 24, "#1D4B2B", 700)
        y += 46
    text(d, (50, y + 20), "외우는 답이 아니라 세우는 순서", 29, "#1D4B2B", 800)
    text(d, (50, y + 70), "받는 것  PDF 전자책 1권, 묶음마다 답변 구조 1장씩", 26, "#2B2B2B", 500, maxw=900)
    save(im, 7)


# 08 목차 미리보기형
def i08():
    im, d = canvas("#FFFFFF")
    d.rectangle([0, 0, 330, H], fill="#1F2A44")
    text(d, (35, 60), "정부지원사업\n사업계획서", 42, "#FFFFFF", 800)
    text(d, (35, 190), "심사표대로\n쓰는 법", 42, "#F2C14E", 800)
    text(d, (35, 560), "PDF 전자책\n배점 표 양식 포함", 26, "#DDE3EF", 500)
    toc = ["사업계획서는 누가 읽는가", "심사표를 배점 표로 바꾸기", "문제 인식", "해결 방안", "성장 전략과 매출",
           "팀 역량", "자금 사용 계획 표", "표·그림 위치", "발표 평가 대비", "제출 전 점검표"]
    text(d, (370, 40), "목차", 30, "#1F2A44", 800)
    y = 95
    for i, t in enumerate(toc, 1):
        text(d, (370, y), f"{i:>2}", 26, "#B38A00", 800)
        text(d, (430, y), t, 26, "#2B2B2B", 500)
        d.line([370, y + 40, 940, y + 40], fill="#D5D9E2", width=1)
        y += 56
    save(im, 8)


# 09 한 장 요약형
def i09():
    im, d = canvas("#E8E8E4")
    text(d, (50, 40), "보고서·기획서\n한 장으로", 54, "#222222", 800)
    text(d, (50, 200), "결론과 요청 사항이\n첫 장에서 읽히게", 30, "#444444", 500)
    text(d, (50, 330), "받는 것", 27, "#C2461E", 800)
    text(d, (50, 375), "PDF 전자책 1권\n보고서·기획서 한 장 양식\n상사가 돌려보낸 사례 6건", 27, "#222222", 500)
    x0, y0, x1, y1 = 520, 40, 940, 710
    d.rectangle([x0, y0, x1, y1], fill="#FFFFFF", outline="#222222", width=3)
    d.rectangle([x0 + 20, y0 + 20, x1 - 20, y0 + 70], fill="#222222")
    text(d, (x0 + 32, y0 + 27), "제목: 결론 한 문장", 22, "#FFFFFF", 700)
    d.rectangle([x0 + 20, y0 + 90, x1 - 20, y0 + 170], fill="#F6D9CE", outline="#C2461E", width=2)
    text(d, (x0 + 32, y0 + 105), "요청 사항 · 결정 기한", 22, "#C2461E", 700)
    d.rectangle([x0 + 20, y0 + 190, x0 + 195, y0 + 450], outline="#888888", width=2)
    d.rectangle([x0 + 205, y0 + 190, x1 - 20, y0 + 450], outline="#888888", width=2)
    text(d, (x0 + 32, y0 + 200), "배경·현황", 21, "#444444", 700)
    text(d, (x0 + 217, y0 + 200), "대안 둘과 추천안", 21, "#444444", 700)
    d.rectangle([x0 + 20, y0 + 470, x1 - 20, y0 + 600], outline="#888888", width=2)
    text(d, (x0 + 32, y0 + 480), "일정 · 비용 · 위험", 21, "#444444", 700)
    save(im, 9)


# 10 격자형 30
def i10():
    im, d = canvas("#14213D")
    text(d, (50, 35), "PPT 한 장 한 메시지", 52, "#FFFFFF", 800)
    text(d, (50, 110), "원칙 다섯 가지와 레이아웃 30", 32, "#FCA311", 700)
    cols, rows = 10, 3
    cw, ch, gap = 76, 52, 14
    x0, y0 = 50, 190
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * (cw + gap)
            y = y0 + r * (ch + gap)
            d.rectangle([x, y, x + cw, y + ch], fill="#FFFFFF")
            k = (r * cols + c) % 6
            if k == 0:
                d.rectangle([x + 8, y + 8, x + cw - 8, y + 20], fill="#14213D")
            elif k == 1:
                d.rectangle([x + 28, y + 12, x + 48, y + 40], fill="#FCA311")
            elif k == 2:
                d.rectangle([x + 8, y + 10, x + 36, y + 42], fill="#14213D")
                d.rectangle([x + 40, y + 10, x + cw - 8, y + 42], fill="#BFC7D8")
            elif k == 3:
                for j in range(3):
                    d.rectangle([x + 8 + j * 22, y + 20, x + 22 + j * 22, y + 32], fill="#14213D")
            elif k == 4:
                for j in range(3):
                    d.rectangle([x + 8, y + 8 + j * 14, x + cw - 8, y + 14 + j * 14], fill="#BFC7D8")
            else:
                d.rectangle([x + 8, y + 8, x + cw - 8, y + 44], fill="#BFC7D8")
    text(d, (50, 440), "받는 것", 28, "#FCA311", 800)
    text(d, (50, 485), "PDF 전자책 1권(가로형)\n장표 전후 비교 5쌍과 점검 체크리스트", 29, "#FFFFFF", 500)
    text(d, (50, 640), "제목은 주장, 본문은 증명, 색은 두 가지까지", 27, "#FFFFFF", 700, maxw=900)
    save(im, 10)


# 11 8칸 구성
def i11():
    im, d = canvas("#FFF8E7")
    text(d, (50, 35), "상세페이지 글은\n여덟 칸으로", 54, "#8A3B12", 800)
    names = ["첫 화면", "불편 공감", "해결 방법", "근거", "사용 방법", "구성품·규격", "자주 묻는 질문", "구매 안내"]
    x0, y0, cw, ch, gap = 50, 215, 205, 105, 20
    for i, n in enumerate(names):
        x = x0 + (i % 4) * (cw + gap)
        y = y0 + (i // 4) * (ch + gap)
        d.rectangle([x, y, x + cw, y + ch], fill="#FFFFFF", outline="#8A3B12", width=3)
        text(d, (x + 14, y + 10), str(i + 1), 34, "#E07B39", 800)
        text(d, (x + 14, y + 58), n, 25, "#2B2B2B", 700)
    text(d, (50, 515), "업종별 문구 틀 7종", 29, "#8A3B12", 800)
    text(d, (50, 560), "식품, 생활용품, 뷰티, 패션, 서비스, 디지털 상품, 지역 업체", 25, "#2B2B2B", 500, maxw=900)
    text(d, (50, 640), "받는 것  PDF 전자책 1권, 칸마다 문장 시작 틀과 점검표", 26, "#2B2B2B", 700, maxw=900)
    save(im, 11)


# 12 말풍선형
def i12():
    im, d = canvas("#ECECF4")
    text(d, (50, 35), "AI 업무 문서\n프롬프트 120", 54, "#2D2A6E", 800)
    d.rounded_rectangle([50, 205, 450, 300], radius=20, fill="#FFFFFF", outline="#8C8CB5", width=2)
    text(d, (70, 225), "보고서 써 줘", 28, "#2B2B2B", 500)
    text(d, (470, 240), "밋밋한 결과", 24, "#8C8CB5", 700)
    d.rounded_rectangle([50, 330, 950, 480], radius=20, fill="#2D2A6E")
    text(d, (75, 345), "역할 · 읽는 사람 · 목적 · 재료 · 형식\n다섯 칸을 채운 질문", 30, "#FFFFFF", 700)
    text(d, (75, 425), "결과가 읽는 사람에게 맞게 달라집니다", 24, "#CFCFF0", 500)
    text(d, (50, 520), "받는 것", 28, "#2D2A6E", 800)
    text(d, (50, 565), "PDF 전자책 1권, 열두 종류 문서별 프롬프트 120개\nAI 티를 줄이는 후속 질문 8개", 27, "#2B2B2B", 500)
    save(im, 12)


# 13 교정 표
def i13():
    im, d = canvas("#FFFFFF")
    text(d, (50, 30), "셀프 교정 150", 56, "#8E1B1B", 800)
    text(d, (50, 105), "보고서·자기소개서 맞춤법·띄어쓰기", 30, "#2B2B2B", 700)
    d.rectangle([50, 175, 950, 220], fill="#8E1B1B")
    text(d, (65, 180), "틀린 문장", 25, "#FFFFFF", 700)
    text(d, (385, 180), "고친 문장", 25, "#FFFFFF", 700)
    text(d, (715, 180), "이유", 25, "#FFFFFF", 700)
    rows = [("할 수 있을 것 같애요", "할 수 있을 것 같아요", "어미"),
            ("안 되요", "안 돼요", "되/돼"),
            ("몇일 걸립니다", "며칠 걸립니다", "표기"),
            ("검토 해 보겠습니다", "검토해 보겠습니다", "띄어쓰기")]
    y = 220
    for a, b, c in rows:
        d.rectangle([50, y, 950, y + 56], outline="#D0D0D0")
        d.text((65, y + 10), a, font=F(24, 500), fill="#8E1B1B")
        wd = tw(d, a, F(24, 500))
        d.line([65, y + 28, 65 + wd, y + 28], fill="#8E1B1B", width=2)
        text(d, (385, y + 10), b, 24, "#1D5A2B", 700)
        text(d, (715, y + 10), c, 24, "#2B2B2B", 500)
        y += 56
    text(d, (50, 480), "갈래 7개, 항목 150개", 29, "#8E1B1B", 800)
    text(d, (50, 525), "띄어쓰기 35, 맞춤법 30, 호응 25, 군더더기 20 외", 25, "#2B2B2B", 500, maxw=900)
    text(d, (50, 610), "받는 것  PDF 전자책 1권, 셀프 교정 순서와 점검표", 27, "#2B2B2B", 700, maxw=900)
    save(im, 13)


# 14 체크리스트형
def i14():
    im, d = canvas("#F5F1E8")
    text(d, (50, 35), "보도자료\n첫 문단", 58, "#1B1B1B", 800)
    text(d, (50, 215), "한 문장에 들어갈 것", 28, "#B5481F", 800)
    items = ["누가", "무엇을", "언제", "어디서", "왜 지금"]
    y = 265
    for it in items:
        d.rectangle([50, y, 84, y + 34], outline="#1B1B1B", width=3)
        d.line([57, y + 18, 66, y + 28], fill="#B5481F", width=4)
        d.line([66, y + 28, 80, y + 6], fill="#B5481F", width=4)
        text(d, (104, y - 2), it, 29, "#1B1B1B", 700)
        y += 58
    d.rectangle([450, 215, 950, 560], fill="#FFFFFF", outline="#1B1B1B", width=3)
    d.rectangle([470, 235, 930, 285], fill="#1B1B1B")
    text(d, (485, 240), "제목 한 줄", 26, "#FFFFFF", 700)
    d.rectangle([470, 310, 930, 400], fill="#F7D9C8", outline="#B5481F", width=2)
    text(d, (485, 320), "첫 문단", 24, "#B5481F", 800)
    for j in range(2):
        d.rectangle([485, 358 + j * 18, 915 - j * 80, 366 + j * 18], fill="#E0A98C")
    for j in range(5):
        d.rectangle([470, 425 + j * 24, 930 - (j % 2) * 120, 433 + j * 24], fill="#D8D8D8")
    text(d, (50, 610), "받는 것  PDF 전자책 1권, 소식 종류별 구성안 6개와 점검표", 27, "#1B1B1B", 700, maxw=900)
    save(im, 14)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in (i01, i02, i03, i04, i05, i06, i07, i08, i09, i10, i11, i12, i13, i14):
        fn()
    print("done")
