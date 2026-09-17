---
name: naver-blog-poster
description: Create, migrate, or edit the user's Naver blog posts with their saved Korean reading format, native subheadings, centered text, and responsive paragraph flow. Use for Naver publishing and readability work, including Tistory migration.
---

# 네이버 블로그 작성과 이전

사용자의 네이버 `pioneer_law` 블로그에 적용하는 개인 작성 규칙이다. 다른 계정을 요청하면 해당 요청을 우선한다.

## 기준과 도구

작업 전에 [형식 기준서](/Users/danny/Documents/PARA/Resource/seomachine-ai-blog/context/naver-reading-format.md)를 읽는다. 기준서는 원본이며 같은 규칙을 별도로 복제하지 않는다.

- 브라우저는 사용 가능한 `ego-browser` 스킬을 읽고 기존 작업 공간을 이어 쓴다.
- 저장된 티스토리 원문 변환: `/Users/danny/Documents/PARA/Resource/seomachine-ai-blog/scripts/naver_format.py`
- 네이버 편집과 검증: 같은 저장소의 `scripts/naver_transfer.mjs`
- 고정 폭 줄바꿈 도구 `scripts/naver_word_wrap.mjs`는 사용자가 폭이 지나치게 좁다고 거부했으므로 사용하지 않는다.
- 기존 이전 여부: `output/naver-migration-20260916/migration-register.csv`와 글별 `published.json`을 확인한다. 이전 기록을 새 글의 발행 승인으로 해석하지 않는다.

## 글 작성

네이버의 `템플릿 → 내 템플릿 → 메모리허브 기본형 · 자연스러운 폭`을 먼저 불러온다. 새 내용으로 바꾸고 안내용 문구를 모두 제거한다. 로컬 원본은 저장소의 `templates/naver/centered-korean.html`이며 HTML의 굵은 제목은 붙여넣은 뒤 실제 소제목으로 변환해야 한다. 템플릿은 서식과 문단 구조를 재사용하는 기능이며 새 문장의 어절 줄바꿈까지 자동으로 보장하지 않는다. 내용 교체 후 줄바꿈 검증을 계속 수행한다.

제목·본문·소제목은 중앙 정렬한다. 본문은 나눔고딕 16px, 행간 180%를 기본으로 한다. 소제목은 SmartEditor의 실제 **소제목** 서식으로 지정한다. 굵은 일반 문단으로 대체하지 않는다. 긴 문단은 두 문장 안팎으로 나누고 문단 사이에 빈 줄을 둔다. 표·코드는 왼쪽 정렬하고 코드의 문자·줄바꿈·들여쓰기를 보존한다.

한국어 띄어쓰기를 교정하고, `그리고`가 `그리 / 고`로 갈라지는 시각적 줄바꿈도 확인한다. 원래 본문 폭을 활용하며 화면 너비에 따라 자연스럽게 줄이 바뀌도록 한다. 240px 같은 짧은 고정 폭이나 글자 수를 기준으로 강제 줄바꿈하지 않는다. 단어 안에 공백이나 보이지 않는 결합 문자를 넣지 않는다. 네이버에서 CSS가 영구 저장된다고 가정하지 않는다. 인기 블로그는 읽기 구성만 참고하고 문구나 이미지를 복제하지 않는다.

## 이전과 검증

원문의 글·링크·이미지와 공개 상태를 보존한다. 공개 이전은 현재 승인 범위 안에서 수행하고 비공개 글을 공개하지 않는다. 기존 글을 고칠 때는 같은 URL을 수정하며 중복 게시물을 만들지 않는다. 새 글 작성·공개·예약 발행 범위를 형식 선호만으로 추론하지 않는다.

먼저 한 글에서 편집 결과를 확인한 다음 같은 방식으로 나머지를 처리한다. 커서 위치나 본문 보존 검사가 실패하면 저장하지 말고 해당 편집을 복구한다. UI 동작 직후에는 구체적인 상태 변화를 기다린다. 대표 이미지를 넣을 때 시각적 End 위치를 쓰면 단어 중간에 이미지가 들어갈 수 있으므로 첫 줄 시작 위치를 확인한다.

발행 후 정확한 URL을 다시 열어 본문·한국어 단어 순서·원문 링크·실제 소제목·이미지·코드·표·중앙 정렬·공개 상태를 확인한다. PC와 모바일에서 문장 줄바꿈을 검증한다. 좁은 표 셀이나 긴 단일 토큰 등의 미해결 예외는 감추지 않는다. 확인한 화면 폭과 결과를 작업 기록에 남긴다.
